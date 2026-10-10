import { useMemo } from "react";
import { Background, Controls, Edge, Handle, Node, NodeProps, Position, ReactFlow } from "@xyflow/react";
import { BMC_LABEL, SessionDetail } from "../api";

export type NodeState = "idle" | "thinking" | "done" | "failed" | "waiting";
type Data = { title: string; sub: string; state: NodeState; kind: string; badge?: string; selected?: boolean };

function AgentNode({ data }: NodeProps<Node<Data>>) {
  const icon = data.state === "done" ? "✓" : data.state === "thinking" ? "●" : data.state === "failed" ? "!" : data.state === "waiting" ? "⏸" : "○";
  return (
    <div className={`node st-${data.state} kind-${data.kind} ${data.selected ? "selected-node" : ""}`}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div className="t"><span>{icon}</span>{data.title}{data.badge && <span className="pill small" style={{ marginLeft: "auto" }}>{data.badge}</span>}</div>
      {data.sub && <div className="s">{data.sub}</div>}
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}
const nodeTypes = { agent: AgentNode };

const POS: Record<string, [number, number]> = {
  problem: [0, 230], workbuddy: [0, 470],
  key_partners: [330, 120], key_activities: [570, 20], key_resources: [570, 220], value_propositions: [810, 120],
  customer_relationships: [1050, 20], channels: [1050, 220], customer_segments: [1290, 120],
  cost_structure: [450, 420], revenue_streams: [1050, 420],
  council_customer: [1580, 0], council_ceo: [1580, 110], council_investor: [1580, 220], council_cfo: [1580, 330], council_mentor: [1580, 440],
  advisor: [1830, 220],
};
const WAVE1 = ["customer_segments", "value_propositions"];
const WAVE2 = ["channels", "customer_relationships", "key_activities", "key_resources", "key_partners"];
const WAVE3 = ["revenue_streams", "cost_structure"];
const SEATS = ["customer", "ceo", "investor", "cfo", "mentor"];

export function deriveStates(d: SessionDetail, live: Record<string, NodeState>): Record<string, NodeState> {
  const s: Record<string, NodeState> = {};
  s.problem = d.problem ? (d.phase === "gate_g1" ? "waiting" : "done") : ["intake", "problem"].includes(d.phase) ? "thinking" : "idle";
  for (const b of d.blocks) s[b.key] = b.status === "done" ? "done" : b.status === "failed" ? "failed" : b.status === "thinking" ? "thinking" : "idle";
  const reviewed = new Set(d.council.map((c) => c.seat));
  for (const seat of SEATS) s[`council_${seat}`] = reviewed.has(seat) ? "done" : d.phase === "council" ? "thinking" : "idle";
  s.advisor = d.phase === "gate_g2" ? "waiting" : d.actions.length ? "done" : d.phase === "advisor" ? "thinking" : "idle";
  const t = d.workbuddy_tasks;
  s.workbuddy = t.some((x) => x.status === "claimed") ? "thinking" : t.some((x) => x.status === "queued") ? "waiting" : t.length ? "done" : "idle";
  for (const [k, v] of Object.entries(live)) if (v === "thinking" && s[k] !== "done") s[k] = "thinking";
  return s;
}

export default function Canvas({ d, live, selected, onSelect }: {
  d: SessionDetail; live: Record<string, NodeState>; selected: string; onSelect: (id: string) => void;
}) {
  const states = deriveStates(d, live);
  const { nodes, edges } = useMemo(() => {
    const sub = (k: string) => d.blocks.find((b) => b.key === k)?.content?.summary ?? "";
    const review = (seat: string) => d.council.find((c) => c.seat === seat);
    const wbActive = d.workbuddy_tasks.filter((x) => x.status === "claimed" || x.status === "queued").map((x) => x.skill).join(", ");
    const data: Record<string, Data> = {
      problem: { title: "Problem Coordinator", sub: d.problem?.statement ?? `${d.intent} · ${d.location_text}`, state: states.problem, kind: "problem" },
      workbuddy: { title: "Tencent WorkBuddy", sub: wbActive ? `Working: ${wbActive}` : d.workbuddy_online ? "Worker online, waiting for tasks" : "Worker offline", state: states.workbuddy, kind: "workbuddy",
        badge: `${d.workbuddy_tasks.filter((x) => x.status === "succeeded").length}/${d.workbuddy_tasks.length}` },
      advisor: { title: "Advisor", sub: d.actions.length ? `${d.actions.length} actions proposed` : "Plans first actions", state: states.advisor, kind: "advisor" },
    };
    for (const k of Object.keys(BMC_LABEL)) {
      const m = d.verdict?.block_means?.[k];
      data[k] = { title: BMC_LABEL[k], sub: sub(k), state: states[k], kind: "bmc", badge: m != null ? `${m}/5` : undefined };
    }
    for (const seat of SEATS) {
      const r = review(seat);
      data[`council_${seat}`] = { title: seat === "ceo" || seat === "cfo" ? seat.toUpperCase() : seat[0].toUpperCase() + seat.slice(1), sub: r ? `Verdict: ${r.verdict}` : "Council seat", state: states[`council_${seat}`], kind: "council", badge: r?.verdict };
    }
    const nodes: Node<Data>[] = Object.entries(data).map(([id, dd]) => ({
      id, type: "agent", position: { x: POS[id][0], y: POS[id][1] }, data: { ...dd, selected: id === selected }, draggable: true,
    }));
    const e: [string, string][] = [];
    WAVE1.forEach((t) => e.push(["problem", t]));
    WAVE2.forEach((t) => WAVE1.forEach((s) => e.push([s, t])));
    WAVE3.forEach((t) => WAVE2.forEach((s) => e.push([s, t])));
    SEATS.forEach((seat) => WAVE3.forEach((s) => e.push([s, `council_${seat}`])));
    SEATS.forEach((seat) => e.push([`council_${seat}`, "advisor"]));
    e.push(["workbuddy", "problem"], ["cost_structure", "workbuddy"]);
    const edges: Edge[] = e.map(([s, t]) => ({
      id: `${s}-${t}`, source: s, target: t, animated: states[t] === "thinking" || (t === "workbuddy" && states.workbuddy === "thinking"),
      style: { stroke: states[t] === "done" ? "var(--ok)" : states[t] === "thinking" ? "var(--accent)" : undefined, strokeWidth: states[t] === "thinking" ? 2 : 1, opacity: states[s] === "idle" ? 0.35 : 1 },
    }));
    return { nodes, edges };
  }, [d, live, selected]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.1 }}
      onNodeClick={(_, n) => onSelect(n.id)} proOptions={{ hideAttribution: true }} minZoom={0.2}>
      <Background gap={24} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
