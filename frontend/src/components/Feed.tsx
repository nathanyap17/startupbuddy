import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { marked } from "marked";
import { AgentEvent, api, BMC_LABEL, SessionDetail } from "../api";

marked.use({ renderer: { html: () => "" } });

const AGENT: Record<string, [string, string]> = {
  problem_coordinator: ["🧭", "Problem Coordinator"], customer_segments: ["👥", "Customer Segments"],
  value_propositions: ["💎", "Value Propositions"], channels: ["📣", "Channels"], customer_relationships: ["🤝", "Customer Relationships"],
  key_activities: ["🛠️", "Key Activities"], key_resources: ["🧰", "Key Resources"], key_partners: ["🔗", "Key Partners"],
  revenue_streams: ["💰", "Revenue Streams"], cost_structure: ["🧾", "Cost Structure"],
  council_customer: ["🛒", "Customer"], council_ceo: ["🧑‍💼", "CEO"], council_investor: ["📈", "Investor"],
  council_cfo: ["🧮", "CFO"], council_mentor: ["🧑‍🏫", "Local Mentor"], council: ["⚖️", "Council"],
  advisor: ["🗓️", "Advisor"], workbuddy: ["🤖", "WorkBuddy"], pipeline: ["🧩", "StartupBuddy"],
  founder: ["🙋", "You"], intake_screener: ["🛡️", "Intake Screener"], follow_up: ["📬", "Follow-up"], session_assistant: ["💬", "StartupBuddy"], pilot_summary: ["✨", "Pilot Summary"],
};
export const agentTag = (a: string) => AGENT[a] ?? ["🤖", a.replace(/_/g, " ")];

type Item =
  | { type: "chat"; ev: AgentEvent }
  | { type: "think"; agent: string; evs: AgentEvent[]; key: string }
  | { type: "line"; ev: AgentEvent };

function group(events: AgentEvent[]): Item[] {
  const out: Item[] = [];
  for (const ev of events) {
    if (ev.kind === "chat") { out.push({ type: "chat", ev }); continue; }
    if (ev.kind === "thinking") {
      const last = out[out.length - 1];
      if (last && last.type === "think" && last.agent === ev.agent) last.evs.push(ev);
      else out.push({ type: "think", agent: ev.agent, evs: [ev], key: `t${ev.seq}` });
      continue;
    }
    out.push({ type: "line", ev });
  }
  return out;
}

function sourcesOf(ev: AgentEvent): string[] {
  const d = ev.detail || {};
  if (Array.isArray(d.sources) && d.sources.length) return d.sources;
  if (d.source) return [d.source];
  if (ev.agent === "workbuddy") return ["Tencent WorkBuddy"];
  return [];
}

function Thinking({ item, live }: { item: Extract<Item, { type: "think" }>; live: boolean }) {
  const [open, setOpen] = useState(live);
  useEffect(() => { if (!live) setOpen(false); }, [live]);
  const [e, n] = agentTag(item.agent);
  const latest = item.evs[item.evs.length - 1].summary;
  const title = (latest.match(/^\*\*(.+?)\*\*/)?.[1] ?? "Thinking").slice(0, 90);
  return (
    <div className={`fd-think ${live ? "live" : ""}`}>
      <button className="fd-think-h" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="fd-tag">{e} {n}</span>
        <span className="fd-think-title">{live ? "is thinking…" : "thought about"} <i>{title}</i></span>
        <span className="fd-caret">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="fd-think-body">
          {item.evs.map((t) => <div key={t.seq} dangerouslySetInnerHTML={{ __html: marked.parse(t.summary) as string }} />)}
        </div>
      )}
    </div>
  );
}

const SUGGESTIONS = ["Honestly, is this idea worth it? 🤔", "What should I verify first?", "How can I beat the nearest competitor?", "Explain my costs simply 💰"];

const errText = (e: unknown) => {
  const m = String(e).match(/\{.*\}/s);
  try { return m ? JSON.parse(m[0]).detail ?? String(e) : String(e); } catch { return String(e); }
};
/** Blocks the council flagged (or scored under 3.5): suggested first for refinement. */
export const needsWork = (d: SessionDetail, key: string) => {
  const m = d.verdict?.block_means?.[key];
  return !!d.verdict?.blocks_to_revise?.includes(key) || (m != null && m < 3.5);
};

export default function Feed({ d, events, running, mention, onMention }: {
  d: SessionDetail; events: AgentEvent[]; running: boolean; mention: string; onMention: (key: string) => void;
}) {
  const sessionId = d.id;
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [pick, setPick] = useState<{ q: string; i: number } | null>(null);
  const [filter, setFilter] = useState<"all" | "chat">("all");
  const end = useRef<HTMLDivElement>(null);
  const ta = useRef<HTMLTextAreaElement>(null);
  const items = useMemo(() => group(events), [events]);
  const shown = filter === "chat" ? items.filter((i) => i.type === "chat") : items;
  const lastThinkKey = [...items].reverse().find((i) => i.type === "think")?.key;
  const options = pick ? Object.keys(BMC_LABEL).filter((k) => {
    const q = pick.q.replace(/[\s_]/g, "");
    return !q || BMC_LABEL[k].toLowerCase().replace(/\s/g, "").includes(q) || k.replace(/_/g, "").includes(q);
  }) : [];
  const flagged = d.refinable ? Object.keys(BMC_LABEL).filter((k) => needsWork(d, k)) : [];

  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [events.length, busy]);
  useEffect(() => { if (mention) { setNote(""); ta.current?.focus(); } }, [mention]);

  async function send(text: string) {
    const t = text.trim();
    if (!t || busy) return;
    setBusy(true); setNote("");
    try {
      if (mention) { await api.refine(sessionId, mention, t); onMention(""); }
      else await api.chat(sessionId, t);
      setMsg("");
    } catch (e) { setNote(errText(e)); }
    setBusy(false);
  }
  const submit = (e: FormEvent) => { e.preventDefault(); send(msg); };
  const choose = (key: string) => {
    const el = ta.current;
    const caret = el?.selectionStart ?? msg.length;
    const before = msg.slice(0, caret).replace(/@[\w ]{0,24}$/, "");
    setMsg((before + msg.slice(caret)).trimStart());
    setPick(null); onMention(key);
  };
  const onType = (v: string, caret: number) => {
    setMsg(v);
    const m = v.slice(0, caret).match(/(?:^|\s)@([\w ]{0,24})$/);
    setPick(m && d.refinable ? { q: m[1].toLowerCase(), i: 0 } : null);
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (pick && options.length) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const step = e.key === "ArrowDown" ? 1 : -1;
        setPick({ ...pick, i: (pick.i + step + options.length) % options.length }); return;
      }
      if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); choose(options[pick.i]); return; }
      if (e.key === "Escape") { setPick(null); return; }
    }
    if (e.key === "Backspace" && mention && !msg) { onMention(""); return; }
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(msg); }
  };
  const refining = d.refining;

  return (
    <div className="fd">
      <div className="panel-h">
        <span>Studio</span>
        <span className={`live-dot ${running ? "on" : ""}`} title={running ? "Agents are working" : "Idle"} />
        <div className="spacer" />
        <div className="seg">
          <button className={filter === "all" ? "on" : ""} onClick={() => setFilter("all")}>Everything</button>
          <button className={filter === "chat" ? "on" : ""} onClick={() => setFilter("chat")}>Chat</button>
        </div>
      </div>
      <div className="fd-list">
        {shown.length === 0 && <div className="fd-empty">👋 Hi! Your agents will show their work here. Ask me anything about your plan, anytime.</div>}
        {shown.map((it) => {
          if (it.type === "chat") {
            const user = it.ev.detail?.role === "user";
            return (
              <div key={it.ev.seq} className={`fd-chat ${user ? "me" : "bot"}`}>
                {!user && <div className="fd-avatar">💬</div>}
                <div className="fd-bubble">
                  {user ? it.ev.summary : <div dangerouslySetInnerHTML={{ __html: marked.parse(it.ev.summary) as string }} />}
                  {it.ev.detail?.channel === "workbuddy" && <span className="chip">via WorkBuddy</span>}
                  {it.ev.detail?.refine && <span className="chip">✏️ refinement</span>}
                </div>
              </div>
            );
          }
          if (it.type === "think") return <Thinking key={it.key} item={it} live={running && it.key === lastThinkKey} />;
          const ev = it.ev;
          const [e, n] = agentTag(ev.agent);
          const src = sourcesOf(ev);
          return (
            <div key={ev.seq} className={`fd-line k-${ev.kind}`}>
              <span className="fd-tag">{e} {n}</span>
              <span className="fd-text">{ev.summary}</span>
              <span className="fd-meta">
                {src.map((s) => <span key={s} className="chip src">{s}</span>)}
                {ev.latency_ms ? <span className="muted">{(ev.latency_ms / 1000).toFixed(1)}s</span> : null}
              </span>
            </div>
          );
        })}
        {busy && <div className="fd-chat bot"><div className="fd-avatar">💬</div><div className="fd-bubble typing"><span /><span /><span /></div></div>}
        <div ref={end} />
      </div>
      {refining && (
        <div className="fd-refining">
          <span className="spin" /> {refining.stage === "rewrite" ? `✍️ Rewriting ${BMC_LABEL[refining.key]}…`
            : refining.stage === "council" ? (refining.mode === "rescore" ? `⚖️ Council re-scoring ${BMC_LABEL[refining.key]}…` : "⚖️ Full council review (round after Checkpoint 2)…")
            : "🔄 Syncing report and summary…"}
        </div>
      )}
      <div className="fd-suggest">
        {!mention && flagged.map((k) => (
          <button key={k} className="chip-btn refine" disabled={busy || !!refining} onClick={() => onMention(k)} title="The council flagged this block">✏️ Refine {BMC_LABEL[k]}</button>
        ))}
        {SUGGESTIONS.map((s) => <button key={s} className="chip-btn" disabled={busy} onClick={() => send(s)}>{s}</button>)}
      </div>
      <form className="fd-compose" onSubmit={submit}>
        {pick && options.length > 0 && (
          <div className="mention-pop" role="listbox" aria-label="Choose a canvas block">
            <div className="mention-h">Refine a canvas block</div>
            {options.map((k, i) => {
              const b = d.blocks.find((x) => x.key === k);
              const m = d.verdict?.block_means?.[k];
              return (
                <button type="button" key={k} role="option" aria-selected={i === pick.i} className={i === pick.i ? "on" : ""}
                  onMouseDown={(e) => { e.preventDefault(); choose(k); }}>
                  <span>{agentTag(k)[0]} {BMC_LABEL[k]}</span>
                  <span className="mention-meta">
                    {(b?.version ?? 1) > 1 && <span className="schip info">v{b?.version}</span>}
                    {m != null && <span className={`schip ${m >= 4 ? "verified" : "info"}`}>{m}/5</span>}
                    {needsWork(d, k) && <span className="schip refine">needs work</span>}
                  </span>
                </button>
              );
            })}
          </div>
        )}
        <div className="fd-input">
          {mention && (
            <div className="mention-chip">
              <span>@{BMC_LABEL[mention]}</span>
              <span className="muted">{d.phase === "gate_g2" || d.phase === "advisor" || d.phase === "deliverables" ? "council re-scores this block" : "full council re-review"}</span>
              <button type="button" className="ghost" aria-label="Remove block" onClick={() => onMention("")}>✕</button>
            </div>
          )}
          <textarea ref={ta} rows={2} value={msg}
            placeholder={mention ? `How should ${BMC_LABEL[mention]} change? e.g. focus on students, cheaper set meals…`
              : d.refinable ? "Ask about your plan, or type @ to refine a block…" : "Ask about your plan…"}
            onChange={(e) => onType(e.target.value, e.target.selectionStart)} onKeyDown={onKey} onBlur={() => setTimeout(() => setPick(null), 120)} />
          {note && <div className="fd-note">🙏 {note}</div>}
        </div>
        <button className="primary" disabled={busy || !msg.trim() || (!!mention && !!refining)}>{mention ? "Refine" : "Send"}</button>
      </form>
    </div>
  );
}
