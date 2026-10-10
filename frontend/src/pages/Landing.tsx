import { Link } from "react-router-dom";
import TopBar from "../components/TopBar";

const REPO = "https://github.com/nathanyap17/startupbuddy";

const LADDER = [
  { t: "Shape the idea", d: "Turn one sentence into a grounded problem statement" },
  { t: "Validate locally", d: "Competitors on Google Maps, Malaysian licences and programmes" },
  { t: "Council review", d: "Customer, CEO, investor, CFO and mentor pressure-test the model" },
  { t: "First meeting booked", d: "Approved meetings and email drafts land in your Google account" },
];

const STEPS = [
  { t: "Ground the idea", d: "A coordinator agent checks your actual neighbourhood: competitors on Google Maps, Malaysian licensing and programmes, plus WorkBuddy desk research. You confirm the problem statement." },
  { t: "Build the canvas", d: "Nine agents write the Business Model Canvas in three dependent waves. Watch each block light up and branch out live." },
  { t: "Face the council", d: "A simulated customer, CEO, investor, CFO and mentor score every block in parallel. Code, not the AI, aggregates the verdict." },
  { t: "Take the first step", d: "The Advisor proposes meetings and email drafts traced to the agents' decisions. Nothing runs until you approve it." },
];

const STATS = [
  { v: "1.4–1.7%", d: "of Malaysian public-university graduates were self-employed in the 2010 and 2013 tracer studies", s: "UNIMAS IJBS; HRMARS" },
  { v: "6%", d: "of youth entrepreneurs obtain financing from financial institutions (KRI, cited)", s: "IIUM repository" },
  { v: "77.4%", d: "of Malaysian MSMEs are microenterprises; MSMEs are 96.2% of all establishments (2025)", s: "SME Corp / DOSM" },
];

export default function Landing() {
  return (
    <>
      <TopBar>
        <a className="hide-sm" href={REPO} target="_blank" rel="noreferrer">GitHub</a>
        <Link to="/app"><button className="primary">Open demo app</button></Link>
      </TopBar>
      <main className="landing">
        <section className="hero">
          <div>
            <div className="hero-brand"><img src="/logo.png" alt="" /><span>StartupBuddy</span></div>
            <h1>From idea to<br />first meeting.</h1>
            <p className="lead">
              An agentic AI solution that takes aspiring Malaysian founders from a vague business idea to a locally
              validated, council-reviewed business model and their first booked stakeholder meetings, powered by Tencent WorkBuddy.
            </p>
            <div className="cta">
              <Link className="btn primary" to="/app">Open demo app</Link>
              <a className="btn" href={REPO} target="_blank" rel="noreferrer">View the code</a>
              <a className="btn" href={`${REPO}/blob/main/docs/WORKBUDDY_INTEGRATION.md`} target="_blank" rel="noreferrer">Connect WorkBuddy</a>
            </div>
            <div className="powered">Powered by Tencent WorkBuddy</div>
          </div>
          <div className="ladder">
            {LADDER.map((r, i) => (
              <div key={r.t} className={`rung ${i === LADDER.length - 1 ? "dark" : ""}`}>
                <div className="n">{String(i + 1).padStart(2, "0")}</div>
                <div><b>{r.t}</b><span>{r.d}</span></div>
              </div>
            ))}
          </div>
        </section>

        <section className="block">
          <div className="eyebrow">The problem</div>
          <h2>Ideas stall before the first real conversation</h2>
          <p className="muted" style={{ maxWidth: 760 }}>
            Young Malaysians who want to start a business get stuck between "I have an idea" and "I'm talking to the
            right people about a validated plan". Generic AI tools write generic plans, help is scattered across agencies,
            and nobody checks the idea against their real street or helps them take the first concrete step.
          </p>
          <div className="grid-4" style={{ marginTop: 18 }}>
            {STATS.map((s) => (
              <div className="card stat" key={s.v}><b>{s.v}</b>{s.d}<div className="muted small" style={{ marginTop: 8 }}>Source: {s.s}</div></div>
            ))}
          </div>
        </section>

        <section className="block">
          <div className="eyebrow">How it works</div>
          <h2>One sentence in, 16 agents at work</h2>
          <div className="grid-4">
            {STEPS.map((s, i) => (
              <div className="card step" key={s.t}><div className="num">{String(i + 1).padStart(2, "0")}</div><h3>{s.t}</h3><p className="muted" style={{ margin: 0 }}>{s.d}</p></div>
            ))}
          </div>
        </section>

        <section className="block">
          <div className="card wb-band">
            <div className="eyebrow" style={{ color: "var(--brand-dim)" }}>Powered by Tencent WorkBuddy</div>
            <h3>WorkBuddy does real work, not just chat</h3>
            <p style={{ marginTop: 0 }}>
              StartupBuddy exposes an MCP server that Tencent WorkBuddy connects to. Start with one prompt in WorkBuddy,
              <i> "Use StartupBuddy: I want to sell kolo mee near Padungan, Kuching"</i>. WorkBuddy then works through
              StartupBuddy's task queue (desk research, the full report, relaying your approvals) while the agents on
              Google Cloud build and review the business model.
            </p>
            <p style={{ marginBottom: 0 }} className="small">
              Every figure is labelled <span className="pill ok">sourced</span> <span className="pill info">estimated</span>{" "}
              <span className="pill warn">needs verification</span>. Emails are drafted, never sent automatically.
            </p>
          </div>
        </section>

        <footer className="footer muted small">
          Team SMILING FACE WITH SUNGLASSES: Nathan Yap, Abraham Pang, Malcolm Sim, Zoe Tan · Dormathon 2026, Track 2 ·
          Built with Google ADK, Gemini on Vertex AI, Cloud Run, Firebase and Tencent WorkBuddy.
        </footer>
      </main>
    </>
  );
}
