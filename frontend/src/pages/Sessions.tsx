import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import TopBar from "../components/TopBar";
import { api, PHASE_LABEL, SessionSummary } from "../api";

export function phaseClass(p: string) {
  if (p === "done") return "ok";
  if (p === "failed") return "bad";
  if (p.startsWith("gate")) return "warn";
  return "info";
}

export default function Sessions() {
  const [list, setList] = useState<SessionSummary[]>([]);
  const [intent, setIntent] = useState("I want to sell kolo mee near Padungan");
  const [loc, setLoc] = useState("Padungan, Kuching");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [wb, setWb] = useState<boolean | null>(null);
  const nav = useNavigate();

  const load = () => api.list().then(setList).catch((e) => setErr(String(e)));
  useEffect(() => {
    load();
    const h = () => api.health().then((x) => setWb(x.workbuddy_online)).catch(() => setWb(null));
    h();
    const t = setInterval(() => { load(); h(); }, 8000);
    return () => clearInterval(t);
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setErr("");
    try { const s = await api.create(intent, loc); nav(`/app/s/${s.id}`); }
    catch (e) { setErr(String(e)); setBusy(false); }
  }

  return (
    <>
      <TopBar>
        <span className={`pill ${wb ? "ok" : "warn"}`}><span className="dot" />WorkBuddy {wb ? "online" : "offline"}</span>
        <span className="pill hide-sm">Demo account</span>
      </TopBar>
      <main className="page">
        <h2>Your startup sessions</h2>
        <p className="muted">Each session is one business idea. Describe what you want to do and where in Malaysia. You can also start one from WorkBuddy.</p>
        <form className="card new-session" onSubmit={submit}>
          <div className="fields">
            <input value={intent} onChange={(e) => setIntent(e.target.value)} placeholder="I want to…" aria-label="Your idea" />
            <input value={loc} onChange={(e) => setLoc(e.target.value)} placeholder="Location, e.g. Padungan, Kuching" aria-label="Location" />
            <button className="primary" disabled={busy || intent.length < 5 || loc.length < 2}>{busy ? "Starting…" : "Start agents"}</button>
          </div>
          {err && <div className="pill bad">{err}</div>}
        </form>
        <div className="session-list">
          {list.map((s) => (
            <Link key={s.id} to={`/app/s/${s.id}`} className="card session-item">
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{s.title}</div>
                <div className="muted small">{s.location_text} · {new Date(s.created_at).toLocaleString("en-MY", { timeZone: "Asia/Kuching" })}{s.origin === "workbuddy" ? " · started in WorkBuddy" : ""}</div>
              </div>
              <span className={`pill ${phaseClass(s.phase)}`}>{PHASE_LABEL[s.phase] ?? s.phase}</span>
            </Link>
          ))}
          {list.length === 0 && <p className="muted">No sessions yet.</p>}
        </div>
      </main>
    </>
  );
}
