export const API = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") || "http://localhost:8000";

export type Phase = "intake" | "screening" | "gate_g0" | "blocked" | "problem" | "gate_g1" | "bmc" | "council" | "deliverables" | "advisor" | "gate_g2" | "actions" | "done" | "failed";

export interface SessionSummary {
  id: string; title: string; intent: string; location_text: string; phase: Phase; origin: string;
  error: string | null; created_at: string; updated_at: string;
  auto_g1: boolean; auto_g2: boolean; summary: PilotSummary | null;
  screen: Screen | null; clarification: string | null;
}
export interface Screen { verdict: "allowed" | "regulated" | "ambiguous" | "prohibited"; interpretation: string; business_type: "physical" | "digital" | "hybrid";
  sector: string; needs_location_scouting: boolean; licences: string[]; regulators: string[]; critical_concerns: string[];
  clarifying_question: string; refusal_reason: string; legal_alternatives: string[]; online_competitor_hints: string[]; }
export interface PilotSummary { one_liner: string; verdict: "go" | "revise" | "stop"; highlights: string[]; first_step: string; }
export interface Evidence { scope: string; claim: string; value: string | null; label: "sourced" | "estimated" | "needs_verification"; source_url: string | null; method: string | null; produced_by: string; }
export interface BlockVersion { version: number; instruction: string | null; change_note: string | null; updated_at: string | null; }
export interface Block { key: string; status: string; round?: number; version?: number; content: { summary?: string; items?: string[]; assumptions?: string[] };
  instruction?: string | null; change_note?: string | null; stale_reason?: string | null; history?: BlockVersion[]; }
export interface Refining { key: string; mode: "rescore" | "retriage"; stage: "rewrite" | "council" | "sync"; }
export interface Review { round?: number; seat: string; scores: Record<string, number>; strengths: string[]; risks: string[]; must_verify: string[]; improve: string[]; verdict: string; }
export interface Action { id: string; kind: "email_outreach" | "site_visit" | "online_meeting" | "task" | "calendar_event" | "gmail_draft"; follow_up: string | null; follow_up_note: string | null; title: string; rationale: string; payload: Record<string, any>; source_agent: string; approval: string; external_ref: string | null; external_url: string | null; outdated?: boolean; }
export interface Competitor { name: string; rating: number | null; reviews: number | null; distance_km: number; maps_url: string | null; }
export interface SessionDetail extends SessionSummary {
  lat: number | null; lng: number | null;
  problem: null | { statement: string; target_user: string; pain: string; why_now: string; confirmed_at: string | null;
    details: { demand_signals?: string[]; competition_summary?: string; differentiation_hypothesis?: string; competitors?: Competitor[] } };
  blocks: Block[]; evidence: Evidence[]; council: Review[];
  verdict: null | { block_means: Record<string, number | null>; blocks_to_revise: string[]; overall: string; round: number; trigger: string | null;
    previous: null | { block_means: Record<string, number | null>; overall: string } };
  refining: Refining | null; refinable: boolean;
  actions: Action[]; artifacts: { id: string; kind: string; filename: string; url: string }[];
  workbuddy_tasks: { id: string; skill: string; status: string; result: any }[];
  workbuddy_online: boolean;
}
export interface AgentEvent { seq: number; ts: string; agent: string; kind: string; target: string | null; summary: string; detail: any; latency_ms: number | null; }

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => j<{ ok: boolean; workbuddy_online: boolean; google_workspace_linked: boolean; model: string }>("/health"),
  list: () => j<SessionSummary[]>("/sessions"),
  create: (intent: string, location_text: string, auto_g1 = false, auto_g2 = false) =>
    j<SessionSummary>("/sessions", { method: "POST", body: JSON.stringify({ intent, location_text, auto_g1, auto_g2 }) }),
  refine: (id: string, key: string, instruction: string) =>
    j<{ ok: boolean; mode: string; message: string }>(`/sessions/${id}/blocks/${key}/refine`, { method: "POST", body: JSON.stringify({ instruction }) }),
  chat: (id: string, message: string) => j<{ reply: string }>(`/sessions/${id}/chat`, { method: "POST", body: JSON.stringify({ message }) }),
  settings: (id: string, body: { auto_g1?: boolean; auto_g2?: boolean }) =>
    j<{ auto_g1: boolean; auto_g2: boolean }>(`/sessions/${id}/settings`, { method: "POST", body: JSON.stringify(body) }),
  get: (id: string) => j<SessionDetail>(`/sessions/${id}`),
  remove: (id: string) => j<{ ok: boolean }>(`/sessions/${id}`, { method: "DELETE" }),
  gate: (id: string, gate: "G0" | "G1" | "G2", body: { decision: string; statement?: string; notes?: string; action_ids?: string[]; always?: boolean }) =>
    j<{ ok: boolean; phase: string }>(`/sessions/${id}/gates/${gate}`, { method: "POST", body: JSON.stringify(body) }),
  checkFollowups: (id: string) => j<{ results: { action_id: string; state: string }[] }>(`/sessions/${id}/followups/check`, { method: "POST" }),
  updateFollowup: (id: string, aid: string, status: "done" | "reschedule" | "cancelled") =>
    j<{ ok: boolean }>(`/sessions/${id}/actions/${aid}/followup`, { method: "POST", body: JSON.stringify({ status }) }),
  retryAction: (id: string, aid: string) => j<{ status?: string; error?: string }>(`/sessions/${id}/actions/${aid}/retry`, { method: "POST" }),
  rerenderDocx: (id: string) => j<{ ok: boolean }>(`/sessions/${id}/report/docx`, { method: "POST" }),
  report: async (id: string) => (await fetch(`${API}/sessions/${id}/report`)).text(),
  eventsUrl: (id: string) => `${API}/sessions/${id}/events`,
};

export const BMC_LABEL: Record<string, string> = {
  customer_segments: "Customer Segments", value_propositions: "Value Propositions", channels: "Channels",
  customer_relationships: "Customer Relationships", key_activities: "Key Activities", key_resources: "Key Resources",
  key_partners: "Key Partners", revenue_streams: "Revenue Streams", cost_structure: "Cost Structure",
};

export const PHASE_LABEL: Record<Phase, string> = {
  intake: "Starting", screening: "Checking your idea", gate_g0: "Waiting for you: one question", blocked: "Can't continue", problem: "Grounding the problem", gate_g1: "Waiting for you: confirm problem",
  bmc: "Building the canvas", council: "Council review", deliverables: "Preparing deliverables",
  advisor: "Advisor planning actions", gate_g2: "Waiting for you: approve actions", actions: "Executing approved actions",
  done: "Done", failed: "Stopped",
};
