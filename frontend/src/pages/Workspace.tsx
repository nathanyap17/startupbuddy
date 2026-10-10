import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import TopBar from "../components/TopBar";
import Canvas, { NodeState } from "../components/Canvas";
import Feed from "../components/Feed";
import RightPane from "../components/RightPane";
import { AgentEvent, api, BMC_LABEL, Evidence, PHASE_LABEL, SessionDetail } from "../api";
import { phaseClass } from "./Sessions";
import "./workspace.css";

const LABEL_CLASS: Record<string, string> = { sourced: "sourced", estimated: "info", needs_verification: "refine" };
const LABEL_SAY: Record<string, string> = { sourced: "Sourced", estimated: "Estimated", needs_verification: "Verify" };
const ACTIVE_KINDS = new Set(["start", "thought", "thinking", "tool_call", "tool_result"]);
const STEPS: { k: string; t: string; phases: string[] }[] = [
  { k: "1", t: "Ground", phases: ["intake", "screening", "gate_g0", "blocked", "problem", "gate_g1"] },
  { k: "2", t: "Build", phases: ["bmc"] },
  { k: "3", t: "Challenge", phases: ["council", "deliverables"] },
  { k: "4", t: "Act", phases: ["advisor", "gate_g2", "actions"] },
  { k: "✓", t: "Pilot", phases: ["done"] },
];

function EvidenceList({ items }: { items: Evidence[] }) {
  if (!items.length) return null;
  return (
    <div className="ev-list">
      {items.map((e, i) => (
        <div key={i} className="ev-item">
          <span className={`schip ${LABEL_CLASS[e.label]}`}>{LABEL_SAY[e.label]}</span> <b>{e.claim}</b>{e.value ? `: ${e.value}` : ""}
          {e.source_url && <div className="small"><a href={e.source_url} target="_blank" rel="noreferrer">source ↗</a> · {e.produced_by}</div>}
          {e.method && <div className="small muted">Method: {e.method}</div>}
        </div>
      ))}
    </div>
  );
}

function Drawer({ d, sel, onClose }: { d: SessionDetail; sel: string; onClose: () => void }) {
  let title = "";
  let body: JSX.Element | null = null;
  if (sel === "screen" && d.screen) {
    const s = d.screen;
    title = "🛡️ Intake check";
    body = (<>
      <p>{s.interpretation}</p>
      <div className="small"><b>Verdict:</b> {s.verdict} · <b>Type:</b> {s.business_type} · <b>Sector:</b> {s.sector}</div>
      {d.clarification && <div className="small"><b>Your clarification:</b> {d.clarification}</div>}
      {s.refusal_reason && <div className="small"><b>Why not:</b> {s.refusal_reason}</div>}
      {s.licences.length > 0 && <><h4>Licences &amp; laws</h4><ul className="small">{s.licences.map((x) => <li key={x}>{x}</li>)}</ul></>}
      {s.regulators.length > 0 && <div className="small"><b>Regulators:</b> {s.regulators.join(", ")}</div>}
      {s.critical_concerns.length > 0 && <><h4>Early red flags</h4><ul className="small">{s.critical_concerns.map((x) => <li key={x}>{x}</li>)}</ul></>}
      <p className="small muted">Guidance, not legal advice. Confirm licences with the regulator.</p>
    </>);
  } else if (sel === "problem" && d.problem) {
    const p = d.problem;
    const comps = p.details.competitors ?? [];
    title = "🧭 Problem statement";
    body = (<>
      <p>{p.statement}</p>
      <div className="small"><b>Target user:</b> {p.target_user}<br /><b>Pain:</b> {p.pain}<br /><b>Why now:</b> {p.why_now}</div>
      {p.details.differentiation_hypothesis && <div className="small"><b>Differentiation:</b> {p.details.differentiation_hypothesis}</div>}
      {comps.length > 0 && <><h4>Nearby competitors <span className="schip sourced">Google Places</span></h4>
        {comps.slice(0, 8).map((c) => <div key={c.name} className="small row"><a href={c.maps_url ?? "#"} target="_blank" rel="noreferrer" style={{ flex: 1 }}>{c.name}</a><span className="muted">{c.rating ?? "-"}★ · {c.reviews ?? 0} · {c.distance_km} km</span></div>)}</>}
      <h4>Evidence</h4><EvidenceList items={d.evidence.filter((e) => e.scope === "problem")} />
    </>);
  } else if (BMC_LABEL[sel]) {
    const c = d.blocks.find((x) => x.key === sel)?.content ?? {};
    title = BMC_LABEL[sel];
    body = (<>
      <p>{c.summary ?? "Not written yet."}</p>
      {c.items?.length ? <ul>{c.items.map((x, i) => <li key={i}>{x}</li>)}</ul> : null}
      {c.assumptions?.length ? <><h4>Assumptions to test</h4><ul className="small">{c.assumptions.map((x, i) => <li key={i}>{x}</li>)}</ul></> : null}
      <EvidenceList items={d.evidence.filter((e) => e.scope === sel)} />
    </>);
  } else if (sel.startsWith("council_")) {
    const r = d.council.find((x) => `council_${x.seat}` === sel);
    title = `⚖️ ${sel.replace("council_", "").toUpperCase()} review`;
    const L = (t: string, xs: string[]) => (xs.length ? <><h4>{t}</h4><ul className="small">{xs.map((x, i) => <li key={i}>{x}</li>)}</ul></> : null);
    body = r ? <>{L("Strengths", r.strengths)}{L("Risks", r.risks)}{L("Must verify", r.must_verify)}{L("Improve", r.improve)}</> : <p className="muted">Still reviewing…</p>;
  } else if (sel === "workbuddy") {
    title = "🤖 Tencent WorkBuddy";
    body = (<>
      <p className="small muted">Agents queue work for WorkBuddy; it pulls tasks over MCP, does them, and posts results back.</p>
      {d.workbuddy_tasks.map((t) => <div key={t.id} className="ev-item"><b>{t.skill.replace("_", " ")}</b> <span className="schip info">{t.status}</span>{t.result?.summary && <div className="small">{t.result.summary}</div>}</div>)}
    </>);
  } else if (sel === "advisor") {
    title = "🗓️ Advisor";
    body = <>{d.actions.map((a) => <div key={a.id} className="ev-item"><b>{a.kind === "calendar_event" ? "📅" : "✉️"} {a.title}</b><div className="small muted">from {a.source_agent.replace(/_/g, " ")} · {a.approval}</div><div className="small">{a.rationale}</div></div>)}</>;
  }
  if (!body) return null;
  return (
    <aside className="drawer" role="dialog" aria-label={title}>
      <div className="drawer-h"><b>{title}</b><button className="ghost" onClick={onClose} aria-label="Close">✕</button></div>
      <div className="drawer-b">{body}</div>
    </aside>
  );
}

export default function Workspace() {
  const { id = "" } = useParams();
  const [d, setD] = useState<SessionDetail | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [live, setLive] = useState<Record<string, NodeState>>({});
  const [sel, setSel] = useState<string>("");
  const refreshTimer = useRef<number | null>(null);

  const refresh = useCallback(() => { api.get(id).then(setD).catch(() => undefined); }, [id]);
  const scheduleRefresh = useCallback(() => {
    if (refreshTimer.current) return;
    refreshTimer.current = window.setTimeout(() => { refreshTimer.current = null; refresh(); }, 500);
  }, [refresh]);

  useEffect(() => {
    refresh();
    setEvents([]);
    const es = new EventSource(api.eventsUrl(id));
    es.onmessage = (m) => {
      const ev: AgentEvent = JSON.parse(m.data);
      setEvents((xs) => (xs.length && xs[xs.length - 1].seq >= ev.seq ? xs : [...xs, ev].slice(-600)));
      if (ev.target) setLive((s) => ({ ...s, [ev.target!]: ACTIVE_KINDS.has(ev.kind) ? "thinking" : ev.kind === "error" ? "failed" : "done" }));
      if (["done", "phase", "error", "fallback", "handoff", "summary", "approval", "thought"].includes(ev.kind)) scheduleRefresh();
    };
    const poll = setInterval(refresh, 10000);
    return () => { es.close(); clearInterval(poll); };
  }, [id, refresh, scheduleRefresh]);

  if (!d) return <><TopBar /><main className="page muted">Loading…</main></>;
  const running = !["done", "failed", "blocked", "gate_g0", "gate_g1", "gate_g2"].includes(d.phase);
  const stepIdx = STEPS.findIndex((s) => s.phases.includes(d.phase));

  return (
    <>
      <TopBar>
        <span className={`pill ${d.workbuddy_online ? "ok" : "warn"} hide-sm`}><span className="dot" />WorkBuddy {d.workbuddy_online ? "online" : "offline"}</span>
        <span className={`pill ${phaseClass(d.phase)}`}>{PHASE_LABEL[d.phase] ?? d.phase}</span>
        <Link className="hide-sm" to="/app"><button className="ghost">All sessions</button></Link>
      </TopBar>
      <div className="ws3">
        <aside className="ws3-left"><Feed sessionId={d.id} events={events} running={running} /></aside>
        <section className="ws3-center">
          <div className="center-top">
            <div className="stepper">
              {STEPS.map((s, i) => (
                <div key={s.t} className={`step ${i < stepIdx || d.phase === "done" ? "past" : i === stepIdx ? "now" : ""}`}><span>{s.k}</span>{s.t}</div>
              ))}
            </div>
            <div className="center-meta"><span className="schip info">{d.title}</span><span className="schip info">📍 {d.location_text}</span></div>
          </div>
          {d.summary && (
            <div className={`pilot pilot-${d.summary.verdict}`}>
              <div className="pilot-k">Pilot summary</div>
              <div className="pilot-line">{d.summary.one_liner}</div>
              <div className="pilot-hl">{d.summary.highlights.map((h) => <span key={h}>{h}</span>)}</div>
              {d.summary.first_step && <div className="small"><b>First step:</b> {d.summary.first_step}</div>}
            </div>
          )}
          {d.error && <div className="pilot pilot-stop"><div className="pilot-line">{d.phase === "blocked" ? "🛑" : "😓"} {d.error}</div></div>}
          <div className="canvas-wrap">
            <Canvas d={d} live={live} selected={sel} onSelect={setSel} />
            {sel && <Drawer d={d} sel={sel} onClose={() => setSel("")} />}
            {!sel && <div className="canvas-hint">Tap any agent card to inspect its work</div>}
          </div>
        </section>
        <aside className="ws3-right"><RightPane d={d} onChanged={refresh} /></aside>
      </div>
    </>
  );
}
