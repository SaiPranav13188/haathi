"""LangGraph nodes (haathi.md §7). Each node emits animation events (§9.5) through the stream writer."""
from __future__ import annotations

import re
import time
from typing import Any, TypedDict

from .. import llm
from ..config import get_settings
from ..eligibility.evaluator import evaluate_all
from ..eligibility.explain import doc_label, rule_label
from ..eligibility.fields import spec_json
from ..eligibility.questioner import next_questions
from ..language.detect import detect
from ..language.facts import extract_facts, extract_with_llm, is_about_self
from ..language.intent import classify
from ..language.translate import query_variants
from ..services import services
from ..verify.verifier import verify
from . import templates as tpl
from .serialize import Citations, scheme_card


class State(TypedDict, total=False):
    # input
    query: str
    ui_lang: str
    profile: dict[str, dict]          # field -> {value, source_text, method}
    pending: list[str]                # fields Haathi asked last turn
    asked: list[str]                  # all fields asked so far
    focus: list[str]                  # scheme ids discussed last turn
    skip_questions: bool
    overrides: dict                   # ablation flags
    # working
    lang: str
    info: dict
    intent: str
    mentions: list[str]
    renamed: list[tuple[str, str]]
    new_facts: list[dict]
    subqueries: list[str]
    queries: list[str]
    english: str
    translate_method: str
    hits: list
    retries: int
    top_score: float
    grade: str
    outcomes: list
    questions: list[str]
    answer: dict
    timings: dict


def _emit(event: dict) -> None:
    try:
        from langgraph.config import get_stream_writer

        get_stream_writer()(event)
    except Exception:  # not streaming (eval / tests)
        pass


def _timed(state: State, name: str, t0: float) -> dict:
    return {**state.get("timings", {}), name: round((time.perf_counter() - t0) * 1000, 1)}


def _profile_values(state: State) -> dict[str, Any]:
    return {k: v["value"] for k, v in (state.get("profile") or {}).items()}


# ---------------------------------------------------------------------------------------------- understand
async def understand(state: State) -> dict:
    t0 = time.perf_counter()
    q = state["query"]
    info = detect(q, state.get("ui_lang"))
    lang = info.lang if (info.lang != "en" or not q.strip()) else ("en" if re.search(r"[A-Za-z]{3,}", q) else state.get("ui_lang", "en"))
    corpus = services().corpus
    hits = corpus.find_mentions(q)
    mentions = [sid for sid, _ in hits]
    renamed = [(sid, old) for sid, old in hits if old]
    if not mentions and state.get("focus") and re.search(r"\b(it|this|that|its|idi|deeni|yeh|iske|uske)\b|దీని|దానికి|ఇది|इसके|इसका|यह", q, re.I):
        mentions = list(state["focus"])
    facts = extract_facts(q, state.get("pending"))
    if llm.available() and (is_about_self(q) or state.get("pending")):
        known = {f.field for f in facts}
        facts += [f for f in await extract_with_llm(q) if f.field not in known]
    profile = dict(state.get("profile") or {})
    for f in facts:
        profile[f.field] = {"value": f.value, "source_text": f.source_text, "method": f.method}
    intent = classify(q, mentions, len(facts))
    if intent == "general" and state.get("pending") and facts:
        intent = "find_schemes"  # an answer to our question
    if intent == "chitchat" and facts:
        intent = "find_schemes"
    if state.get("skip_questions") and profile and intent in {"general", "chitchat"}:
        # "Show results now": answer from what we already know instead of treating it as a new question
        intent = "scheme_eligibility" if mentions else "find_schemes"
    _emit({"type": "stage", "stage": "understand", "lang": lang, "script": info.script,
           "code_mixed": info.code_mixed, "romanized": info.romanized, "intent": intent,
           "facts": [f.as_dict() for f in facts]})
    return {"info": info.as_dict(), "lang": lang, "mentions": mentions, "renamed": renamed, "intent": intent,
            "new_facts": [f.as_dict() for f in facts], "profile": profile, "retries": 0,
            "timings": _timed(state, "understand", t0)}


def route_after_understand(state: State) -> str:
    return "respond" if state["intent"] == "chitchat" else "decompose"


# ---------------------------------------------------------------------------------------------- decompose
async def decompose(state: State) -> dict:
    q = state["query"]
    corpus = services().corpus
    subs: list[str] = []
    if len(state.get("mentions", [])) > 1:
        aspect = re.sub("|".join(re.escape(corpus.schemes[m].name.en) for m in state["mentions"]), "", q, flags=re.I)
        subs = [f"{corpus.schemes[m].name.en} {aspect}".strip() for m in state["mentions"]]
    else:
        parts = [p.strip() for p in re.split(r"[?？।]\s+|\balso\b|\band also\b", q) if len(p.strip()) > 3]
        subs = parts if len(parts) > 1 else [q]
    _emit({"type": "stage", "stage": "decompose", "count": len(subs)})
    return {"subqueries": subs}


# ---------------------------------------------------------------------------------------------- retrieve
async def retrieve(state: State) -> dict:
    t0 = time.perf_counter()
    sv = services()
    s = get_settings()
    from ..language.detect import LangInfo

    info = LangInfo(**state["info"])
    retriever = sv.retriever(state.get("overrides"))
    strategy = (state.get("overrides") or {}).get("crosslingual", s.crosslingual)
    queries: list[str] = []
    english = ""
    method = "none"
    for sub in state.get("subqueries") or [state["query"]]:
        variants, eng, method = await query_variants(sub, info, strategy)
        queries += variants
        english = (english + " " + eng).strip()
    if state.get("retries"):
        queries += state.get("queries", [])[-1:]
    hits = retriever.search(queries)
    # schemes the user named get their passages pulled in even if retrieval missed them
    mentioned_docs = {sv.corpus.schemes[m].doc for m in state.get("mentions", [])}
    if mentioned_docs:
        have = {h.chunk.id for h in hits}
        from ..retrieval.pipeline import Hit

        for c in sv.corpus.chunks:
            if c.doc_id in mentioned_docs and c.id not in have and c.kind != "card":
                hits.append(Hit(c, 0.0, sources={"mention": 1}))
    _emit({"type": "stage", "stage": "retrieve", "count": len(hits)})
    return {"hits": hits, "queries": queries, "english": english, "translate_method": method,
            "timings": _timed(state, "retrieve", t0)}


async def rerank(state: State) -> dict:
    t0 = time.perf_counter()
    retriever = services().retriever(state.get("overrides"))
    q = [state["query"], state.get("english") or state["query"]]
    hits = retriever.rerank(q, state["hits"], keep=max(get_settings().rerank_keep, 8 if state.get("mentions") else 0))
    _emit({"type": "stage", "stage": "rerank", "order": [h.chunk.id for h in hits]})
    return {"hits": hits, "top_score": hits[0].score if hits else 0.0, "timings": _timed(state, "rerank", t0)}


# chosen from the risk–coverage sweep for each reranker (eval/risk_coverage.py)
TUNED_THRESHOLDS = {"lexical": 0.50, "bge-reranker-v2-m3": 0.24}


async def grade(state: State) -> dict:
    s = get_settings()
    thr = (state.get("overrides") or {}).get("abstain_threshold", s.abstain_threshold)
    if thr is None:
        name = getattr(services().retriever(state.get("overrides")).reranker, "name", "lexical")
        thr = TUNED_THRESHOLDS.get(name, 0.5)
    structured = state["intent"] in {"find_schemes"} or bool(state.get("mentions"))
    good = structured or state.get("top_score", 0.0) >= thr
    _emit({"type": "stage", "stage": "grade", "score": round(state.get("top_score", 0.0), 3), "good": good})
    return {"grade": "good" if good else "weak"}


def route_after_grade(state: State) -> str:
    corrective = (state.get("overrides") or {}).get("corrective", get_settings().corrective)
    if state["grade"] == "good":
        return "eligibility"
    if corrective and state.get("retries", 0) < 1:
        return "rewrite"
    return "abstain"


async def rewrite(state: State) -> dict:
    from ..language.translate import glossary_translate

    q = state.get("english") or state["query"]
    new = None
    if llm.available():
        new = await llm.complete(f"Rewrite this question about Indian government welfare schemes as a short keyword search query "
                                 f"in English (add likely scheme names or synonyms). Reply with only the query.\n\n{state['query']}")
    if not new:
        new = " ".join(dict.fromkeys(f"{glossary_translate(state['query'])} {q}".split()))
    _emit({"type": "stage", "stage": "retry", "reason": "low_relevance"})
    return {"subqueries": [new.strip()], "retries": state.get("retries", 0) + 1}


async def abstain(state: State) -> dict:
    lang = state["lang"]
    _emit({"type": "result", "kind": "unsure"})
    return {"answer": {"text": tpl.UNSURE[lang], "citations": [], "cards": [], "abstained": True,
                       "official_links": tpl.OFFICIAL_LINKS, "kind": "unsure"}}


# ---------------------------------------------------------------------------------------------- eligibility
async def eligibility(state: State) -> dict:
    t0 = time.perf_counter()
    corpus = services().corpus
    intent = state["intent"]
    if state.get("mentions"):
        schemes = [corpus.schemes[m] for m in state["mentions"]]
    elif intent == "find_schemes":
        schemes = list(corpus.schemes.values())
    else:
        # general questions: evaluate schemes behind the top passages so cards can show status
        ids = []
        for h in state.get("hits", [])[:4]:
            if h.chunk.scheme_id and h.chunk.scheme_id not in ids:
                ids.append(h.chunk.scheme_id)
        schemes = [corpus.schemes[i] for i in ids]
    outcomes = evaluate_all(schemes, _profile_values(state))
    _emit({"type": "stage", "stage": "eligibility", "eligible": sum(o.status == "eligible" for o in outcomes),
           "maybe": sum(o.status == "maybe" for o in outcomes)})
    return {"outcomes": outcomes, "timings": _timed(state, "eligibility", t0)}


def route_after_eligibility(state: State) -> str:
    if state["intent"] not in {"find_schemes", "scheme_eligibility"} or state.get("skip_questions"):
        return "generate"
    if len(state.get("asked") or []) >= get_settings().max_questions:
        return "generate"
    if any(o.status == "maybe" for o in state["outcomes"]):
        return "ask"
    return "generate"


async def ask(state: State) -> dict:
    corpus = services().corpus
    profile = _profile_values(state)
    schemes = [o.scheme for o in state["outcomes"]] if state.get("mentions") else list(corpus.schemes.values())
    budget = get_settings().max_questions - len(state.get("asked") or [])
    k = 2 if len(profile) <= 2 and budget >= 2 else 1
    fields = next_questions(profile, schemes, k=min(k, budget))
    _emit({"type": "stage", "stage": "ask", "fields": fields})
    return {"questions": fields}


def route_after_ask(state: State) -> str:
    return "generate"


# ---------------------------------------------------------------------------------------------- generate
def _best_hit_for(scheme_id: str, hits) -> Any:
    return next((h for h in hits if h.chunk.scheme_id == scheme_id and h.chunk.kind != "card"), None)


async def generate(state: State) -> dict:
    t0 = time.perf_counter()
    lang = state["lang"]
    corpus = services().corpus
    cites = Citations(corpus)
    outcomes = state.get("outcomes", [])
    intent = state["intent"]
    lines: list[str] = []
    cards: list[dict] = []
    claims: list[dict] = []  # {text, citation, structured}
    kind = "info"

    for sid, old in state.get("renamed", []):
        sc = corpus.schemes[sid]
        lines.append(tpl.RENAMED[lang].format(old=old, name=sc.name.get(lang), date=sc.changed_on))

    questions = state.get("questions") or []
    if intent in {"find_schemes", "scheme_eligibility"}:
        eligible = [o for o in outcomes if o.status == "eligible"]
        maybe = [o for o in outcomes if o.status == "maybe"]
        # "almost eligible" only when that one change would make the person eligible, not merely "still unknown"
        almost = [o for o in outcomes if o.status == "not_eligible" and o.what_if and o.what_if["would_be"] == "eligible"]
        if questions:
            kind = "asking"
            n = len(questions)
            intro = tpl.ASK_INTRO[lang].format(n=n, s=tpl.plural(n, lang))
            if n == 1:
                intro = {"en": "To check the right schemes, one quick question:", "hi": "सही योजनाएँ जाँचने के लिए एक छोटा सवाल:",
                         "te": "సరైన పథకాలు చూడటానికి ఒక చిన్న ప్రశ్న:"}[lang]
            lines.append(intro)
            lines += [spec_json(f, lang)["question"] for f in questions]
            if eligible or maybe:
                lines.append(tpl.SO_FAR[lang].format(e=len(eligible), m=len(maybe)))
            cards = [scheme_card(o, lang, cites) for o in eligible[:6]]
        else:
            if eligible:
                kind = "eligible"
                n = len(eligible)
                lines.append(tpl.ELIGIBLE_ONE[lang].format(name=eligible[0].scheme.name.get(lang)) if n == 1
                             else tpl.ELIGIBLE_HEAD[lang].format(n=n, s=tpl.plural(n, lang)))
                for i, o in enumerate(eligible[:8], 1):
                    cid = cites.add(o.scheme.benefit.source, o.scheme.scheme_id)
                    text = f"{i}. " + tpl.BENEFIT[lang].format(name=o.scheme.name.get(lang), benefit=o.scheme.benefit.summary.get(lang))
                    lines.append(f"{text} [{cid}]")
                    claims.append({"text": o.scheme.benefit.summary.en, "citation": cid, "structured": True})
            elif maybe:
                kind = "maybe"
            else:
                kind = "not_eligible"
                lines.append(tpl.NONE_FOUND[lang] if almost else tpl.NONE_AT_ALL[lang])
            if maybe and not questions:
                lines.append(tpl.MAYBE_HEAD[lang].format(names=tpl.join([o.scheme.name.get(lang) for o in maybe[:4]], lang)))
            if almost:
                lines.append(tpl.ALMOST[lang])
                for o in almost[:3]:
                    card = scheme_card(o, lang, cites)
                    lines.append(f"• {card['what_if']['text']} [{card['what_if']['citation']}]")
            docs: list[str] = []
            for o in eligible[:8]:
                for d in o.scheme.documents_required:
                    if d not in docs:
                        docs.append(d)
            if docs:
                lines.append(tpl.DOCS[lang].format(docs=", ".join(doc_label(d, lang) for d in docs[:6])))
            cards = [scheme_card(o, lang, cites) for o in eligible[:8] + maybe[:4] + almost[:3]]
    elif state.get("mentions"):
        for o in outcomes:
            sc = o.scheme
            name = sc.name.get(lang)
            if intent == "documents":
                cid = cites.add(sc.how_to_apply.source, sc.scheme_id)
                lines.append(tpl.DOCS_FOR[lang].format(name=name, docs=", ".join(doc_label(d, lang) for d in sc.documents_required)) + f" [{cid}]")
            elif intent == "how_to_apply":
                cid = cites.add(sc.how_to_apply.source, sc.scheme_id)
                lines.append(tpl.APPLY_FOR[lang].format(name=name, how=sc.how_to_apply.summary.get(lang)) + f" [{cid}]")
                claims.append({"text": sc.how_to_apply.summary.en, "citation": cid, "structured": True})
            else:  # benefit / scheme_info
                cid = cites.add(sc.benefit.source, sc.scheme_id)
                lines.append(tpl.BENEFIT[lang].format(name=name, benefit=sc.benefit.summary.get(lang)) + f" [{cid}]")
                claims.append({"text": sc.benefit.summary.en, "citation": cid, "structured": True})
                if intent == "scheme_info":
                    r_cids = [cites.add(r.source, sc.scheme_id) for r in sc.rules[:3]]
                    rules_txt = "; ".join(rule_label(r, lang) for r in sc.rules[:4])
                    lines.append(tpl.ELIG_FOR[lang].format(name=name, rules=rules_txt) + f" [{r_cids[0]}]")
            if sc.changed_on and sc.change_note:
                lines.append("🦎 " + tpl.CHANGED[lang].format(date=sc.changed_on, note=sc.change_note.get(lang)))
            cards.append(scheme_card(o, lang, cites))
    else:
        kind = "info"
        text, cl = await _free_answer(state, cites)
        if not cl:  # nothing usable in the passages: abstain instead of guessing
            _emit({"type": "result", "kind": "unsure"})
            return {"answer": {"text": tpl.UNSURE[lang], "citations": [], "cards": [], "claims": [], "questions": [],
                               "abstained": True, "official_links": tpl.OFFICIAL_LINKS, "kind": "unsure"},
                    "timings": _timed(state, "generate", t0)}
        lines.append(text)
        claims += cl
        cards = [scheme_card(o, lang, cites) for o in outcomes[:3]]

    _emit({"type": "stage", "stage": "generate"})
    answer = {"text": "\n".join(lines), "citations": cites.items, "cards": cards, "claims": claims,
              "questions": [spec_json(f, lang) for f in questions], "abstained": False, "kind": kind}
    return {"answer": answer, "timings": _timed(state, "generate", t0)}


GEN_PROMPT = """You answer questions about Indian government schemes using ONLY the numbered passages.
Answer in {lang_name}, in 2-4 short sentences, simple words. After each sentence put the passage number in
square brackets like [2]. If the passages do not answer the question, reply exactly: NOT_FOUND.
Never invent amounts, ages or limits.

Passages:
{passages}

Question: {q}"""


async def _free_answer(state: State, cites: Citations) -> tuple[str, list[dict]]:
    lang = state["lang"]
    hits = [h for h in state.get("hits", []) if h.chunk.kind != "card"][:5]
    numbered = []
    for h in hits:
        cid = cites.add({"doc": h.chunk.doc_id, "page": h.chunk.page, "quote": None}, h.chunk.scheme_id,
                        structured=False, text=h.chunk.text)
        numbered.append((cid, h))
    if llm.available() and numbered:
        out = await llm.complete(GEN_PROMPT.format(
            lang_name={"en": "English", "hi": "Hindi", "te": "Telugu"}[lang],
            passages="\n".join(f"[{cid}] {h.chunk.text}" for cid, h in numbered), q=state["query"]))
        if out and "NOT_FOUND" not in out:
            claims = []
            for sent in re.split(r"(?<=[.!?।])\s+", out.strip()):
                m = re.search(r"\[(\d+)\]", sent)
                if m:
                    claims.append({"text": sent, "citation": int(m.group(1)), "structured": False})
            return out.strip(), claims
    # extractive fallback: best sentences from the top passages (English source text)
    from ..retrieval.tokenize import tokenize

    qt = set(tokenize(state.get("english") or state["query"]))
    picked = []
    for cid, h in numbered[:3]:
        sents = re.split(r"(?<=[.!?])\s+", h.chunk.text)
        best = max(sents, key=lambda s: len(qt & set(tokenize(s))), default="")
        if best and len(qt & set(tokenize(best))) > 0:
            picked.append((cid, best))
        if len(picked) == 2:
            break
    if not picked:
        return tpl.UNSURE[lang], []
    note = tpl.EXTRACTIVE_NOTE[lang]
    text = " ".join(f"{s} [{cid}]" for cid, s in picked) + (f" {note}" if note else "")
    return text, [{"text": s, "citation": cid, "structured": False} for cid, s in picked]


# ---------------------------------------------------------------------------------------------- verify
async def verify_node(state: State) -> dict:
    t0 = time.perf_counter()
    ans = dict(state["answer"])
    do_verify = (state.get("overrides") or {}).get("verify", get_settings().verify)
    corpus = services().corpus
    by_id = {c["id"]: c for c in ans.get("citations", [])}
    for c in ans.get("citations", []):
        doc = corpus.docs.get(c["doc"])
        page_text = doc.page(c["page"]).text if doc else ""
        if c["structured"] and c.get("quote"):
            c["status"] = "supported" if " ".join(c["quote"].split()) in " ".join(page_text.split()) else "unsupported"
        else:
            c["status"] = "supported" if c.get("passage") else "unclear"
    removed = 0
    if do_verify:
        for cl in ans.get("claims", []):
            c = by_id.get(cl["citation"])
            if not c:
                cl["status"] = "unsupported"
                continue
            passage = c.get("quote") if cl["structured"] else (c.get("passage") or c.get("quote") or "")
            cl["status"] = await verify(cl["text"], passage or "", structured=cl["structured"])
            if cl["status"] == "unsupported":
                c["status"] = "unsupported"
                if not cl["structured"] and cl["text"] in ans["text"]:
                    ans["text"] = ans["text"].replace(cl["text"], "").strip()
                    removed += 1
    for c in ans.get("citations", []):
        _emit({"type": "stage", "stage": "verify", "citation_id": c["id"], "status": c["status"]})
        c.pop("passage", None)
    ans["removed_claims"] = removed
    if do_verify and not ans["text"].strip():
        ans["text"] = tpl.UNSURE[state["lang"]]
        ans["abstained"] = True
    return {"answer": ans, "timings": _timed(state, "verify", t0)}


# ---------------------------------------------------------------------------------------------- respond
async def respond(state: State) -> dict:
    lang = state["lang"]
    ans = state.get("answer")
    if state["intent"] == "chitchat" or ans is None:
        is_thanks = re.search(r"thank|dhanyavad|ధన్యవాద|धन्यवाद|शुक्रिया|thx", state["query"], re.I)
        ans = {"text": (tpl.THANKS if is_thanks else tpl.GREETING)[lang], "citations": [], "cards": [], "claims": [],
               "questions": [], "abstained": False, "kind": "greeting"}
    for word in re.split(r"(\s+)", ans["text"]):
        if word:
            _emit({"type": "token", "text": word})
    kind = ans.get("kind")
    result_kind = {"eligible": "eligible", "not_eligible": "not_eligible", "unsure": "unsure", "asking": "asking",
                   "maybe": "maybe"}.get(kind, "info")
    _emit({"type": "result", "kind": result_kind, "schemes": sum(c["status"] == "eligible" for c in ans.get("cards", []))})
    ans["disclaimer"] = tpl.DISCLAIMER[lang]
    return {"answer": ans}
