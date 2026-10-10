import { useMemo } from "react";
import { Background, BackgroundVariant, Controls, Edge, Handle, Node, NodeProps, Position, ReactFlow } from "@xyflow/react";
import { BMC_LABEL, SessionDetail } from "../api";

export type NodeState = "idle" | "thinking" | "done" | "failed" | "waiting";
type Chip = { t: string; c: "verified" | "sourced" | "refine" | "info" };
type Data = { title: string; emoji: string; sub: string; state: NodeState; kind: string; chips: Chip[]; selected?: boolean };

/** Small blueprint-style robot: blinks and bobs while its agent is working. */
export function Robot({ state, emoji }: { state: NodeState; emoji: string }) {
  return (
    <div className={`robot r-${state}`} aria-hidden="true">
      <svg viewBox="0 0 40 40" width="34" height="34">
        <line x1="20" y1="3" x2="20" y2="9" className="r-ant" />
        <circle cx="20" cy="3" r="2.4" className="r-bulb" />
        <rect x="7" y="9" width="26" height="21" rx="7" className="r-head" />
        <circle cx="15" cy="19" r="2.6" className="r-eye" />
        <circle cx="25" cy="19" r="2.6" className="r-eye" />
        <path d="M15 25 Q20 28 25 25" className="r-mouth" />
        <rect x="12" y="31" width="16" height="6" rx="2" className="r-body" />
      </svg>
      <span className="robot-emoji">{emoji}</span>
    </div>
  );
}

function AgentNode({ data }: NodeProps<Node<Data>>) {
  const loading = data.state === "thinking" && !data.sub;
  return (
    <div className={`node st-${data.state} kind-${data.kind} ${data.selected ? "selected-node" : ""}`}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div className="node-h">
        <Robot state={data.state} emoji={data.emoji} />
        <div className="node-tt">
          <div className="t">{data.title}</div>
          <div className="node-state">{data.state === "thinking" ? "working…" : data.state === "waiting" ? "waiting for you" : data.state === "failed" ? (data.kind === "screen" ? "blocked" : "needs a retry") : "done"}</div>
        </div>
      </div>
      {loading ? (
        <div className="bones"><i /><i /><i style={{ width: "60%" }} /></div>
      ) : (
        data.sub && <div className="s">{data.sub}</div>
      )}
      {data.chips.length > 0 && <div className="node-chips">{data.chips.map((c) => <span key={c.t} className={`schip ${c.c}`}>{c.t}</span>)}</div>}
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}
const nodeTypes = { agent: AgentNode };

const POS: Record<string, [number, number]> = {
  screen: [-330, 250], problem: [0, 250], workbuddy: [0, 520],
  key_partners: [330, 130], key_activities: [580, 10], key_resources: [580, 250], value_propositions: [830, 130],
  customer_relationships: [1080, 10], channels: [1080, 250], customer_segments: [1330, 130],
  cost_structure: [460, 470], revenue_streams: [1080, 470],
  council_customer: [1630, 0], council_ceo: [1630, 125], council_investor: [1630, 250], council_cfo: [1630, 375], council_mentor: [1630, 500],
  advisor: [1900, 250],
};
const EMOJI: Record<string, string> = {
  screen: "🛡️", problem: "🧭", workbuddy: "🤖", advisor: "🗓️", customer_segments: "👥", value_propositions: "💎", channels: "📣",
  customer_relationships: "🤝", key_activities: "🛠️", key_resources: "🧰", key_partners: "🔗", revenue_streams: "💰",
  cost_structure: "🧾", council_customer: "🛒", council_ceo: "🧑‍💼", council_investor: "📈", council_cfo: "🧮", council_mentor: "🧑‍🏫",
};
const SEAT_NAME: Record<string, string> = { customer: "Customer", ceo: "CEO", investor: "Investor", cfo: "CFO", mentor: "Local Mentor" };
const WAVE1 = ["customer_segments", "value_propositions"];
const WAVE2 = ["channels", "customer_relationships", "key_activities", "key_resources", "key_partners"];
const WAVE3 = ["revenue_streams", "cost_structure"];
export const SEATS = ["customer", "ceo", "investor", "cfo", "mentor"];

export function deriveStates(d: SessionDetail, live: Record<string, NodeState>): Record<string, NodeState> {
  const s: Record<string, NodeState> = {};
  s.screen = d.phase === "screening" || d.phase === "intake" ? "thinking" : d.phase === "gate_g0" ? "waiting"
    : d.phase === "blocked" ? "failed" : d.screen ? "done" : "idle";
  s.problem = d.problem ? (d.phase === "gate_g1" ? "waiting" : "done") : ["intake", "problem"].includes(d.phase) ? "thinking" : "idle";
  for (const b of d.blocks) s[b.key] = b.status === "done" ? "done" : b.status === "failed" ? "failed" : b.status === "thinking" ? "thinking" : "idle";
  const reviewed = new Set(d.council.map((c) => c.seat));
  for (const seat of SEATS) s[`council_${seat}`] = reviewed.has(seat) ? "done" : d.phase === "council" ? "thinking" : "idle";
  s.advisor = d.phase === "gate_g2" ? "waiting" : d.actions.length ? "done" : d.phase === "advisor" ? "thinking" : "idle";
  const t = d.workbuddy_tasks;
  s.workbuddy = t.some((x) => x.status === "claimed") ? "thinking" : t.some((x) => x.status === "queued") ? "waiting" : t.length ? "done" : "idle";
  for (const [k, v] of Object.entries(live)) if (v === "thinking" && s[k] !== "done" && s[k] !== undefined) s[k] = "thinking";
  return s;
}

function blockChips(d: SessionDetail, key: string): Chip[] {
  const chips: Chip[] = [];
  const ev = d.evidence.filter((e) => e.scope === key);
  const sourced = ev.filter((e) => e.label === "sourced").length;
  const m = d.verdict?.block_means?.[key];
  if (m != null && m >= 4) chips.push({ t: `Verified ${m}/5`, c: "verified" });
  else if (m != null) chips.push({ t: `${m}/5`, c: "info" });
  if (sourced) chips.push({ t: `Sourced ×${sourced}`, c: "sourced" });
  if (d.verdict?.blocks_to_revise?.includes(key) || (m != null && m < 3.5)) chips.push({ t: "Refinement flag", c: "refine" });
  return chips;
}

export default function Canvas({ d, live, selected, onSelect }: {
  d: SessionDetail; live: Record<string, NodeState>; selected: string; onSelect: (id: string) => void;
}) {
  const states = deriveStates(d, live);
  const { nodes, edges } = useMemo(() => {
    const sub = (k: string) => d.blocks.find((b) => b.key === k)?.content?.summary ?? "";
    const wb = d.workbuddy_tasks;
    const sc = d.screen;
    const data: Record<string, Data> = {
      screen: { title: "Intake Screener", emoji: EMOJI.screen,
        sub: sc ? (sc.verdict === "ambiguous" ? sc.clarifying_question : sc.verdict === "prohibited" ? sc.refusal_reason : sc.interpretation) : "",
        state: states.screen, kind: "screen",
        chips: sc ? [
          { t: sc.verdict === "prohibited" ? "Blocked" : sc.verdict === "ambiguous" ? "Needs clarity" : sc.verdict === "regulated" ? "Regulated" : "Cleared",
            c: sc.verdict === "allowed" ? "verified" : sc.verdict === "regulated" ? "refine" : sc.verdict === "prohibited" ? "refine" : "info" },
          { t: { physical: "Physical", digital: "Digital", hybrid: "Hybrid" }[sc.business_type], c: "info" },
        ] : [] },
      problem: { title: "Problem Coordinator", emoji: EMOJI.problem, sub: d.problem?.statement ?? "", state: states.problem, kind: "problem",
        chips: d.problem ? [{ t: `Sourced ×${d.evidence.filter((e) => e.scope === "problem" && e.label === "sourced").length}`, c: "sourced" }] : [] },
      workbuddy: { title: "Tencent WorkBuddy", emoji: EMOJI.workbuddy,
        sub: wb.filter((x) => x.status === "claimed").map((x) => `Working on ${x.skill.replace("_", " ")}`).join(" · ") || `${wb.filter((x) => x.status === "succeeded").length}/${wb.length} tasks done`,
        state: states.workbuddy, kind: "workbuddy", chips: [] },
      advisor: { title: "Advisor", emoji: EMOJI.advisor, sub: d.actions.length ? `${d.actions.length} first steps proposed` : "", state: states.advisor, kind: "advisor", chips: [] },
    };
    for (const k of Object.keys(BMC_LABEL)) data[k] = { title: BMC_LABEL[k], emoji: EMOJI[k], sub: sub(k), state: states[k], kind: "bmc", chips: blockChips(d, k) };
    for (const seat of SEATS) {
      const r = d.council.find((c) => c.seat === seat);
      const scores = r ? Object.values(r.scores) : [];
      const avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : null;
      data[`council_${seat}`] = { title: SEAT_NAME[seat], emoji: EMOJI[`council_${seat}`], sub: r ? (r.risks[0] ?? "") : "", state: states[`council_${seat}`], kind: "council",
        chips: r ? [{ t: r.verdict.toUpperCase(), c: r.verdict === "go" ? "verified" : r.verdict === "stop" ? "refine" : "info" }, ...(avg ? [{ t: `avg ${avg}`, c: "info" as const }] : [])] : [] };
    }
    // Progressive reveal: a node exists only once its step has been reached.
    const visible = Object.keys(data).filter((id) => states[id] !== "idle");
    const vis = new Set(visible);
    const nodes: Node<Data>[] = visible.map((id) => ({
      id, type: "agent", position: { x: POS[id][0], y: POS[id][1] }, data: { ...data[id], selected: id === selected }, draggable: true,
    }));
    const e: [string, string][] = [];
    e.push(["screen", "problem"]);
    WAVE1.forEach((t) => e.push(["problem", t]));
    WAVE2.forEach((t) => WAVE1.forEach((s) => e.push([s, t])));
    WAVE3.forEach((t) => WAVE2.forEach((s) => e.push([s, t])));
    SEATS.forEach((seat) => WAVE3.forEach((s) => e.push([s, `council_${seat}`])));
    SEATS.forEach((seat) => e.push([`council_${seat}`, "advisor"]));
    e.push(["workbuddy", "problem"], ["cost_structure", "workbuddy"]);
    const edges: Edge[] = e.filter(([s, t]) => vis.has(s) && vis.has(t)).map(([s, t]) => ({
      id: `${s}-${t}`, source: s, target: t, animated: states[t] === "thinking",
      style: { stroke: states[t] === "thinking" ? "var(--brand-2)" : "var(--brand-dim)", strokeWidth: states[t] === "thinking" ? 2 : 1.2, opacity: states[t] === "done" ? 0.55 : 1 },
    }));
    return { nodes, edges };
  }, [d, live, selected]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.15, maxZoom: 1 }}
      onNodeClick={(_, n) => onSelect(n.id)} proOptions={{ hideAttribution: true }} minZoom={0.2} key={nodes.length}>
      <Background variant={BackgroundVariant.Lines} gap={28} className="blueprint" />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
