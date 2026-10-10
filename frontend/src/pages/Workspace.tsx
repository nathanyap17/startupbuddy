import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import TopBar from "../components/TopBar";
import Canvas, { NodeState } from "../components/Canvas";
import { AgentEvent, api, BMC_LABEL, Evidence, PHASE_LABEL, SessionDetail } from "../api";
import { phaseClass } from "./Sessions";

const LABEL_CLASS: Record<string, string> = { sourced: "ok", estimated: "info", needs_verification: "warn" };
const THINKING_KINDS = new Set(["start", "thought", "tool_call", "tool_result"]);

function EvidenceList({ items }: { items: Evidence[] }) {
  if (!items.length) return null;
  return (
    <div style={{ display: "grid", gap: 6 }}>
      {items.map((e, i) => (
        <div key={i} className="ev-item">
          <span className={`pill ${LABEL_CLASS[e.label]}`}>{e.label.replace("_", " ")}</span>{" "}
          <b>{e.claim}</b>{e.value ? `: ${e.value}` : ""}
          {e.source_url && <div className="small"><a href={e.source_url} target="_blank" rel="noreferrer">source</a> · {e.produced_by}</div>}
          {e.method && <div className="small muted">Method: {e.method}</div>}
        </div>
      ))}
    </div>
  );
}

function GateG1({ d, onDone }: { d: SessionDetail; onDone: () => void }) {
  const [text, setText] = useState(d.problem?.statement ?? "");
  const [busy, setBusy] = useState(false);
  const send = async (decision: string) => {
    setBusy(true);
    await api.gate(d.id, "G1", { decision, statement: decision === "edit" ? text : undefined }).catch(alert);
    onDone();
  };
  const edited = text.trim() !== (d.problem?.statement ?? "").trim();
  return (
    <div className="gate">
      <h3>Checkpoint G1 · Confirm the problem statement</h3>
      <p className="small" style={{ margin: 0 }}>The canvas agents start only after you confirm. Edit it if it's not quite right.</p>
      <textarea rows={7} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="row">
        <button className="primary" disabled={busy} onClick={() => send(edited ? "edit" : "approve")}>{edited ? "Save edit & continue" : "Confirm & continue"}</button>
        <button className="ghost danger" disabled={busy} onClick={() => send("reject")}>Stop here</button>
      </div>
    </div>
  );
}

function GateG2({ d, onDone }: { d: SessionDetail; onDone: () => void }) {
  const pending = d.actions.filter((a) => a.approval === "pending");
  const [chosen, setChosen] = useState<Set<string>>(new Set(pending.map((a) => a.id)));
  const [busy, setBusy] = useState(false);
  const toggle = (id: string) => setChosen((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const send = async () => {
    setBusy(true);
    await api.gate(d.id, "G2", { decision: "approve", action_ids: [...chosen] }).catch(alert);
    onDone();
  };
  return (
    <div className="gate">
      <h3>Checkpoint G2 · Approve first actions</h3>
      <p className="small" style={{ margin: 0 }}>Only ticked actions run. Calendar events are created in your Google Calendar; emails are saved as Gmail <b>drafts</b>, never sent.</p>
      {pending.map((a) => (
        <div className="action" key={a.id}>
          <label>
            <input type="checkbox" checked={chosen.has(a.id)} onChange={() => toggle(a.id)} />
            <span><b>{a.kind === "calendar_event" ? "📅" : "✉️"} {a.title}</b>
              <div className="small muted">{a.kind === "calendar_event" && a.payload.start_iso ? new Date(a.payload.start_iso).toLocaleString("en-MY", { timeZone: "Asia/Kuching", dateStyle: "medium", timeStyle: "short" }) + " · " : ""}from {a.source_agent}</div>
              <div className="small">{a.rationale}</div>
              {a.kind === "gmail_draft" && <div className="small muted">To: {a.payload.email_to || "(you fill in)"} · {a.payload.email_subject}</div>}
            </span>
          </label>
        </div>
      ))}
      <div className="row">
        <button className="primary" disabled={busy} onClick={send}>Approve {chosen.size} selected</button>
      </div>
    </div>
  );
}

function Inspector({ d, sel }: { d: SessionDetail; sel: string }) {
  if (sel === "problem" && d.problem) {
    const p = d.problem;
    const comps = p.details.competitors ?? [];
    return (
      <div className="inspector">
        <h3>Problem statement</h3>
        <p style={{ margin: 0 }}>{p.statement}</p>
        <div className="small"><b>Target user:</b> {p.target_user}<br /><b>Pain:</b> {p.pain}<br /><b>Why now:</b> {p.why_now}</div>
        {p.details.differentiation_hypothesis && <div className="small"><b>Differentiation hypothesis:</b> {p.details.differentiation_hypothesis}</div>}
        {comps.length > 0 && <>
          <h3>Nearby competitors (Google Maps)</h3>
          <div style={{ display: "grid", gap: 4 }}>
            {comps.slice(0, 8).map((c) => (
              <div key={c.name} className="small row"><a href={c.maps_url ?? "#"} target="_blank" rel="noreferrer" style={{ flex: 1 }}>{c.name}</a><span className="muted">{c.rating ?? "-"}★ · {c.reviews ?? 0} · {c.distance_km} km</span></div>
            ))}
          </div>
        </>}
        <h3>Evidence</h3>
        <EvidenceList items={d.evidence.filter((e) => e.scope === "problem")} />
      </div>
    );
  }
  if (BMC_LABEL[sel]) {
    const b = d.blocks.find((x) => x.key === sel);
    const c = b?.content ?? {};
    return (
      <div className="inspector">
        <h3>{BMC_LABEL[sel]} {d.verdict?.block_means?.[sel] != null && <span className="pill brand">{d.verdict.block_means[sel]}/5</span>}</h3>
        <p style={{ margin: 0 }}>{c.summary ?? "Not written yet."}</p>
        {c.items?.length ? <ul>{c.items.map((x, i) => <li key={i}>{x}</li>)}</ul> : null}
        {c.assumptions?.length ? <><b className="small">Assumptions to test</b><ul className="small">{c.assumptions.map((x, i) => <li key={i}>{x}</li>)}</ul></> : null}
        <EvidenceList items={d.evidence.filter((e) => e.scope === sel)} />
      </div>
    );
  }
  if (sel.startsWith("council_")) {
    const r = d.council.find((x) => `council_${x.seat}` === sel);
    if (!r) return <div className="inspector muted">This council seat hasn't reviewed yet.</div>;
    const L = (t: string, xs: string[]) => xs.length ? <><b className="small">{t}</b><ul className="small">{xs.map((x, i) => <li key={i}>{x}</li>)}</ul></> : null;
    return (
      <div className="inspector">
        <h3>{r.seat.toUpperCase()} · <span className={`pill ${r.verdict === "go" ? "ok" : r.verdict === "stop" ? "bad" : "warn"}`}>{r.verdict}</span></h3>
        {L("Strengths", r.strengths)}{L("Risks", r.risks)}{L("Must verify", r.must_verify)}{L("Improve", r.improve)}
      </div>
    );
  }
  if (sel === "advisor") {
    return (
      <div className="inspector">
        <h3>Advisor actions</h3>
        {d.actions.map((a) => (
          <div className="action" key={a.id}>
            <b>{a.kind === "calendar_event" ? "📅" : "✉️"} {a.title}</b>
            <span className="small muted">from {a.source_agent} · <span className={`pill ${a.approval === "executed" ? "ok" : a.approval === "rejected" ? "" : a.approval === "exec_failed" ? "bad" : "warn"}`}>{a.approval}</span></span>
            {a.external_url && <a className="small" href={a.external_url} target="_blank" rel="noreferrer">Open in Google</a>}
            {a.approval === "exec_failed" && <span className="small muted">{a.external_ref}</span>}
          </div>
        ))}
        {!d.actions.length && <p className="muted">No actions yet.</p>}
      </div>
    );
  }
  if (sel === "workbuddy") {
    return (
      <div className="inspector">
        <h3>WorkBuddy tasks</h3>
        <p className="small muted" style={{ margin: 0 }}>Agents queue work for Tencent WorkBuddy; WorkBuddy pulls it over MCP, does it, and posts results back.</p>
        {d.workbuddy_tasks.map((t) => (
          <div className="action" key={t.id}><b>{t.skill}</b><span className={`pill ${t.status === "succeeded" ? "ok" : t.status === "claimed" ? "info" : t.status === "queued" ? "warn" : "bad"}`}>{t.status}</span>
            {t.result?.summary && <span className="small">{t.result.summary}</span>}
            {t.result?.local_file_paths?.length ? <span className="small muted">Files on the WorkBuddy machine: {t.result.local_file_paths.join(", ")}</span> : null}
          </div>
        ))}
      </div>
    );
  }
  return <div className="inspector muted">Select a node on the canvas.</div>;
}

export default function Workspace() {
  const { id = "" } = useParams();
  const [d, setD] = useState<SessionDetail | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [live, setLive] = useState<Record<string, NodeState>>({});
  const [sel, setSel] = useState("problem");
  const refreshTimer = useRef<number | null>(null);

  const refresh = useCallback(() => { api.get(id).then(setD).catch(() => undefined); }, [id]);
  const scheduleRefresh = useCallback(() => {
    if (refreshTimer.current) return;
    refreshTimer.current = window.setTimeout(() => { refreshTimer.current = null; refresh(); }, 600);
  }, [refresh]);

  useEffect(() => {
    refresh();
    setEvents([]);
    const es = new EventSource(api.eventsUrl(id));
    es.onmessage = (m) => {
      const ev: AgentEvent = JSON.parse(m.data);
      setEvents((xs) => [ev, ...xs].slice(0, 400));
      if (ev.target) setLive((s) => ({ ...s, [ev.target!]: THINKING_KINDS.has(ev.kind) ? "thinking" : ev.kind === "error" ? "failed" : "done" }));
      if (["done", "phase", "error", "fallback", "handoff"].includes(ev.kind)) scheduleRefresh();
    };
    const poll = setInterval(refresh, 10000);
    return () => { es.close(); clearInterval(poll); };
  }, [id, refresh, scheduleRefresh]);

  useEffect(() => {
    if (d?.phase === "gate_g2" || d?.phase === "actions") setSel("advisor");
  }, [d?.phase]);

  if (!d) return <><TopBar /><main className="page muted">Loading…</main></>;

  return (
    <>
      <TopBar>
        <span className={`pill ${d.workbuddy_online ? "ok" : "warn"}`}><span className="dot" />WorkBuddy {d.workbuddy_online ? "online" : "offline"}</span>
        <span className={`pill ${phaseClass(d.phase)}`}>{PHASE_LABEL[d.phase] ?? d.phase}</span>
        <Link to={`/app/s/${d.id}/report`}><button>Report</button></Link>
        <Link className="hide-sm" to="/app"><button className="ghost">All sessions</button></Link>
      </TopBar>
      <div className="ws">
        <aside className="ws-col">
          <div className="panel-h">Agent activity <span className="muted small">({events.length})</span></div>
          <div className="timeline">
            {events.map((e) => (
              <div key={e.seq} className={`ev k-${e.kind}`}>
                <span className="who">{e.agent}</span> <span className="muted">· {new Date(e.ts).toLocaleTimeString("en-MY", { timeZone: "Asia/Kuching" })}{e.latency_ms ? ` · ${(e.latency_ms / 1000).toFixed(1)}s` : ""}</span>
                <div>{e.summary}</div>
              </div>
            ))}
            {!events.length && <p className="muted small">Waiting for agents…</p>}
          </div>
        </aside>
        <section className="ws-canvas">
          <div className="status-bar">
            <span className="pill brand">{d.title}</span>
            <span className="pill">{d.location_text}</span>
            {d.verdict && <span className={`pill ${d.verdict.overall === "go" ? "ok" : d.verdict.overall === "stop" ? "bad" : "warn"}`}>Council: {d.verdict.overall}</span>}
            {d.error && <span className="pill bad">{d.error}</span>}
          </div>
          <Canvas d={d} live={live} selected={sel} onSelect={setSel} />
        </section>
        <aside className="ws-col">
          <div className="panel-h">Inspector</div>
          <div style={{ padding: 14, display: "grid", gap: 14 }}>
            {d.phase === "gate_g1" && <GateG1 d={d} onDone={refresh} />}
            {d.phase === "gate_g2" && <GateG2 d={d} onDone={refresh} />}
          </div>
          <Inspector d={d} sel={sel} />
        </aside>
      </div>
    </>
  );
}
