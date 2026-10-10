import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, SessionDetail } from "../api";
import { SEATS } from "./Canvas";

const SEAT: Record<string, [string, string]> = {
  customer: ["🛒", "Customer"], ceo: ["🧑‍💼", "CEO"], investor: ["📈", "Investor"], cfo: ["🧮", "CFO"], mentor: ["🧑‍🏫", "Local Mentor"],
};
const VERDICT: Record<string, [string, string]> = { go: ["🎉 GO", "verified"], revise: ["🔧 REVISE", "info"], stop: ["🛑 STOP", "refine"] };

function Toggle({ on, label, onChange }: { on: boolean; label: string; onChange: (v: boolean) => void }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={on} onChange={(e) => onChange(e.target.checked)} />
      <span className="track"><span className="thumb" /></span>
      <span>{label}</span>
    </label>
  );
}

function GateG1({ d, onDone }: { d: SessionDetail; onDone: () => void }) {
  const [text, setText] = useState(d.problem?.statement ?? "");
  const [busy, setBusy] = useState(false);
  const edited = text.trim() !== (d.problem?.statement ?? "").trim();
  const send = async (decision: string, always = false) => {
    setBusy(true);
    await api.gate(d.id, "G1", { decision: decision === "approve" && edited ? "edit" : decision, statement: edited ? text : undefined, always }).catch((e) => alert(String(e)));
    onDone();
  };
  return (
    <div className="gate">
      <div className="gate-k">Checkpoint 1 of 2</div>
      <h3>Does this sound like your problem? 🤔</h3>
      <p className="small muted">I grounded it in your neighbourhood. Edit anything that's off, then let the canvas agents start.</p>
      <textarea rows={7} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="gate-actions">
        <button className="primary" disabled={busy} onClick={() => send("approve")}>{edited ? "Save & approve" : "Approve"}</button>
        <button disabled={busy} onClick={() => send("approve", true)} title="Approve now and auto-approve this checkpoint for the rest of this session">Always allow</button>
        <button className="ghost danger" disabled={busy} onClick={() => send("reject")}>Stop</button>
      </div>
    </div>
  );
}

function GateG2({ d, onDone }: { d: SessionDetail; onDone: () => void }) {
  const pending = d.actions.filter((a) => a.approval === "pending");
  const [chosen, setChosen] = useState<Set<string>>(new Set(pending.map((a) => a.id)));
  const [busy, setBusy] = useState(false);
  const toggle = (id: string) => setChosen((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const send = async (always = false) => {
    setBusy(true);
    const ids = always ? pending.map((a) => a.id) : [...chosen];
    await api.gate(d.id, "G2", { decision: "approve", action_ids: ids, always }).catch((e) => alert(String(e)));
    onDone();
  };
  return (
    <div className="gate">
      <div className="gate-k">Checkpoint 2 of 2</div>
      <h3>Which of these may I do for you? ✅</h3>
      <p className="small muted">Only ticked items run, in your Google account. Emails are saved as <b>drafts</b>, never sent.</p>
      <div className="checklist">
        {pending.map((a) => (
          <label key={a.id} className={`check ${chosen.has(a.id) ? "on" : ""}`}>
            <input type="checkbox" checked={chosen.has(a.id)} onChange={() => toggle(a.id)} />
            <span>
              <b>{a.kind === "calendar_event" ? "📅" : "✉️"} {a.title}</b>
              <span className="small muted">
                {a.kind === "calendar_event" && a.payload.start_iso ? new Date(a.payload.start_iso).toLocaleString("en-MY", { timeZone: "Asia/Kuching", dateStyle: "medium", timeStyle: "short" }) + " · Meet link · " : "Gmail draft · "}
                from {a.source_agent.replace(/_/g, " ")}
              </span>
              <span className="small">{a.rationale}</span>
            </span>
          </label>
        ))}
      </div>
      <div className="gate-actions">
        <button className="primary" disabled={busy} onClick={() => send(false)}>Approve {chosen.size} selected</button>
        <button disabled={busy} onClick={() => send(true)} title="Approve all now and auto-approve future actions in this session">Always allow</button>
      </div>
    </div>
  );
}

function Scorecards({ d }: { d: SessionDetail }) {
  if (!d.council.length && d.phase !== "council") return null;
  const v = d.verdict;
  return (
    <section className="rp-sec">
      <div className="rp-h"><span>⚖️ Council verdict</span>{v && <span className={`schip ${VERDICT[v.overall][1]}`}>{VERDICT[v.overall][0]}</span>}</div>
      <div className="score-grid">
        {SEATS.map((seat) => {
          const r = d.council.find((c) => c.seat === seat);
          const vals = r ? Object.values(r.scores) : [];
          const avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
          return (
            <div key={seat} className={`score ${r ? "" : "pending"}`}>
              <div className="score-top"><span>{SEAT[seat][0]} {SEAT[seat][1]}</span>{r && <span className={`schip ${VERDICT[r.verdict][1]}`}>{r.verdict}</span>}</div>
              <div className="bar"><i style={{ width: `${(avg / 5) * 100}%` }} /></div>
              <div className="small muted">{r ? `${avg.toFixed(1)} / 5 · ${r.risks[0] ?? ""}` : "reviewing…"}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Actions({ d, onChanged }: { d: SessionDetail; onChanged: () => void }) {
  const done = d.actions.filter((a) => a.approval !== "pending");
  if (!done.length) return null;
  const chip = (s: string) => (s === "executed" ? "verified" : s === "exec_failed" ? "refine" : s === "rejected" ? "muted" : "info");
  const say: Record<string, string> = { executed: "done ✓", exec_failed: "failed", rejected: "skipped", approved: "running…" };
  return (
    <section className="rp-sec">
      <div className="rp-h"><span>🗓️ Your first steps</span></div>
      <div className="checklist">
        {done.map((a) => (
          <div key={a.id} className="check static">
            <span>
              <b>{a.kind === "calendar_event" ? "📅" : "✉️"} {a.title}</b>
              <span className="row" style={{ gap: 6 }}>
                <span className={`schip ${chip(a.approval)}`}>{say[a.approval] ?? a.approval}</span>
                {a.external_url && <a className="small" href={a.external_url} target="_blank" rel="noreferrer">Open in Google ↗</a>}
                {a.approval === "exec_failed" && <button className="small" onClick={() => api.retryAction(d.id, a.id).then(onChanged).catch((e) => alert(String(e)))}>Retry</button>}
              </span>
              {a.approval === "exec_failed" && <span className="small muted">{a.external_ref}</span>}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function RightPane({ d, onChanged }: { d: SessionDetail; onChanged: () => void }) {
  const [a1, setA1] = useState(d.auto_g1);
  const [a2, setA2] = useState(d.auto_g2);
  useEffect(() => { setA1(d.auto_g1); setA2(d.auto_g2); }, [d.auto_g1, d.auto_g2]);
  const set = async (k: "auto_g1" | "auto_g2", v: boolean) => {
    (k === "auto_g1" ? setA1 : setA2)(v);
    await api.settings(d.id, { [k]: v }).catch(() => undefined);
    onChanged();
  };
  const docx = d.artifacts.find((x) => x.kind === "report");
  return (
    <div className="rp">
      <div className="panel-h"><span>Decisions</span></div>
      <div className="rp-body">
        {d.phase === "gate_g1" && <GateG1 d={d} onDone={onChanged} />}
        {d.phase === "gate_g2" && <GateG2 d={d} onDone={onChanged} />}
        <section className="rp-sec">
          <div className="rp-h"><span>🛂 Autopilot</span></div>
          <Toggle on={a1} label="Always allow Checkpoint 1 (problem)" onChange={(v) => set("auto_g1", v)} />
          <Toggle on={a2} label="Always allow Checkpoint 2 (actions)" onChange={(v) => set("auto_g2", v)} />
          <p className="small muted" style={{ margin: 0 }}>Auto-approvals are logged in the Studio feed. Emails always stay as drafts.</p>
        </section>
        <Scorecards d={d} />
        <Actions d={d} onChanged={onChanged} />
        {(d.phase === "done" || docx) && (
          <section className="rp-sec">
            <div className="rp-h"><span>📄 Report</span></div>
            <div className="row" style={{ flexWrap: "wrap" }}>
              <Link to={`/app/s/${d.id}/report`}><button>Open report</button></Link>
              {docx && <a href={docx.url}><button className="primary">Download DOCX</button></a>}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
