"""Assemble the LangGraph agent (haathi.md §3 / §7)."""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from . import nodes as n


@lru_cache
def build_graph():
    g = StateGraph(n.State)
    g.add_node("understand", n.understand)
    g.add_node("decompose", n.decompose)
    g.add_node("retrieve", n.retrieve)
    g.add_node("rerank", n.rerank)
    g.add_node("grade", n.grade)
    g.add_node("rewrite", n.rewrite)
    g.add_node("abstain", n.abstain)
    g.add_node("eligibility", n.eligibility)
    g.add_node("ask", n.ask)
    g.add_node("generate", n.generate)
    g.add_node("verify", n.verify_node)
    g.add_node("respond", n.respond)

    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", n.route_after_understand, {"respond": "respond", "decompose": "decompose"})
    g.add_edge("decompose", "retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_edge("rerank", "grade")
    g.add_conditional_edges("grade", n.route_after_grade, {"eligibility": "eligibility", "rewrite": "rewrite", "abstain": "abstain"})
    g.add_edge("rewrite", "retrieve")
    g.add_edge("abstain", "respond")
    g.add_conditional_edges("eligibility", n.route_after_eligibility, {"ask": "ask", "generate": "generate"})
    g.add_edge("ask", "generate")
    g.add_edge("generate", "verify")
    g.add_edge("verify", "respond")
    g.add_edge("respond", END)
    return g.compile()


def langfuse_config() -> dict:
    """Attach Langfuse tracing when enabled (self-hosted, free)."""
    from ..config import get_settings

    if not get_settings().langfuse_enabled:
        return {}
    try:
        from langfuse.callback import CallbackHandler
    except ImportError:  # pragma: no cover
        return {}
    return {"callbacks": [CallbackHandler()]}
