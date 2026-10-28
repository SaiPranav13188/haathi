export type Lang = "en" | "hi" | "te";
export type Status = "eligible" | "maybe" | "not_eligible";
export type AnimLevel = "full" | "calm" | "off";

export interface Fact { value: unknown; source_text: string; method: string }
export type Profile = Record<string, Fact>;

export interface RuleRow {
  id: string; field: string; label: string; result: "pass" | "fail" | "unknown";
  user_value: string | null; citation: number; quote: string | null;
}
export interface WhatIf {
  rule_id: string; field: string; threshold: number | number[]; current: number;
  direction: string; would_be: string; text: string; citation: number;
}
export interface SchemeCard {
  scheme_id: string; status: Status; status_label: string; name: string; name_en: string; tagline: string;
  level: "central" | "state"; state: string | null; categories: string[];
  benefit: string; amount: number | null; unit: string | null; per_acre: boolean; benefit_citation: number;
  rules: RuleRow[]; logic: string; missing_fields: string[];
  documents: { key: string; label: string }[]; how_to_apply: string; apply_citation: number;
  official_url: string; last_verified: string; review_status: string;
  changed_on: string | null; change_note: string | null; what_if: WhatIf | null;
  official_sources?: { doc: string; url: string; label: string; downloaded: string }[];
}
export interface Citation {
  id: number; doc: string; page: number; quote: string; bbox: number[] | null; scheme_id: string | null;
  title: string; source_url: string | null; kind: string; structured: boolean;
  status: "pending" | "supported" | "unsupported" | "unclear";
}
export interface Question {
  field: string; kind: "number" | "bool" | "choice"; question: string; label: string;
  options: { value: unknown; label: string }[]; buckets: { value: number; label: string }[];
  unit: string | null; min: number | null; max: number | null; step: number | null; help: string | null;
}
export interface DonePayload {
  type: "done"; lang: Lang; intent: string; text: string; cards: SchemeCard[]; citations: Citation[];
  questions: Question[]; abstained: boolean; official_links: { label: string; url: string }[]; kind: string;
  disclaimer: string; profile_updates: { field: string; value: unknown; source_text: string; method: string }[];
  focus: string[]; trace: Record<string, unknown>;
}
export type StreamEvent =
  | { type: "stage"; stage: string; [k: string]: unknown }
  | { type: "token"; text: string }
  | { type: "result"; kind: string; schemes?: number }
  | { type: "error"; message: string }
  | DonePayload;

export interface ChatMessage {
  id: string; role: "user" | "assistant"; text: string; lang?: Lang; streaming?: boolean;
  done?: DonePayload; error?: string; detected?: { lang: string; romanized: boolean; code_mixed: boolean };
  feedback?: "up" | "down";
}

export interface PageLayout {
  doc_id: string; title: string; source_url: string | null; kind: string; pages: number[]; page: number;
  width: number; height: number;
  blocks: { id: string; type: string; font_size: number; bbox: number[]; lines: { text: string; bbox: number[] }[] }[];
  highlights: { block: string; line: number; start: number; end: number; bbox: number[] }[];
  highlight_bbox: number[] | null; scheme_id: string | null; last_verified: string | null; file_url: string | null;
}
