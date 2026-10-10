import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { marked } from "marked";
import { AgentEvent, api } from "../api";

marked.use({ renderer: { html: () => "" } });

const AGENT: Record<string, [string, string]> = {
  problem_coordinator: ["🧭", "Problem Coordinator"], customer_segments: ["👥", "Customer Segments"],
  value_propositions: ["💎", "Value Propositions"], channels: ["📣", "Channels"], customer_relationships: ["🤝", "Customer Relationships"],
  key_activities: ["🛠️", "Key Activities"], key_resources: ["🧰", "Key Resources"], key_partners: ["🔗", "Key Partners"],
  revenue_streams: ["💰", "Revenue Streams"], cost_structure: ["🧾", "Cost Structure"],
  council_customer: ["🛒", "Customer"], council_ceo: ["🧑‍💼", "CEO"], council_investor: ["📈", "Investor"],
  council_cfo: ["🧮", "CFO"], council_mentor: ["🧑‍🏫", "Local Mentor"], council: ["⚖️", "Council"],
  advisor: ["🗓️", "Advisor"], workbuddy: ["🤖", "WorkBuddy"], pipeline: ["🧩", "StartupBuddy"],
  founder: ["🙋", "You"], session_assistant: ["💬", "StartupBuddy"], pilot_summary: ["✨", "Pilot Summary"],
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

export default function Feed({ sessionId, events, running }: { sessionId: string; events: AgentEvent[]; running: boolean }) {
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<"all" | "chat">("all");
  const end = useRef<HTMLDivElement>(null);
  const items = useMemo(() => group(events), [events]);
  const shown = filter === "chat" ? items.filter((i) => i.type === "chat") : items;
  const lastThinkKey = [...items].reverse().find((i) => i.type === "think")?.key;

  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [events.length, busy]);

  async function send(text: string) {
    const t = text.trim();
    if (!t || busy) return;
    setBusy(true); setMsg("");
    try { await api.chat(sessionId, t); } catch { /* reply arrives via the event stream; errors shown there */ }
    setBusy(false);
  }
  const submit = (e: FormEvent) => { e.preventDefault(); send(msg); };

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
      <div className="fd-suggest">
        {SUGGESTIONS.map((s) => <button key={s} className="chip-btn" disabled={busy} onClick={() => send(s)}>{s}</button>)}
      </div>
      <form className="fd-compose" onSubmit={submit}>
        <textarea rows={2} value={msg} placeholder="Ask about your plan…" onChange={(e) => setMsg(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(msg); } }} />
        <button className="primary" disabled={busy || !msg.trim()}>Send</button>
      </form>
    </div>
  );
}
