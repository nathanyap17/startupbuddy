import { Link } from "react-router-dom";
import TopBar from "../components/TopBar";

const REPO = "https://github.com/nathanyap17/startupbuddy";

const STEPS = [
  { t: "Ground the idea", d: "A coordinator agent checks your actual neighbourhood: competitors on Google Maps, Malaysian licensing and programmes, plus WorkBuddy desk research. You confirm the problem statement." },
  { t: "Build the canvas", d: "Nine agents write the Business Model Canvas in three dependent waves. Watch each block light up and branch out live." },
  { t: "Face the council", d: "A simulated customer, CEO, investor, CFO and mentor score every block in parallel. Code, not the AI, aggregates the verdict." },
  { t: "Take the first step", d: "The Advisor proposes meetings and email drafts traced to the agents' decisions. Nothing runs until you approve it, then it lands in Google Calendar and Gmail." },
];

const STATS = [
  { v: "1.4–1.7%", d: "of Malaysian public-university graduates were self-employed in the 2010 and 2013 tracer studies", s: "UNIMAS IJBS; HRMARS" },
  { v: "6%", d: "of youth entrepreneurs obtain financing from financial institutions (KRI, cited)", s: "IIUM repository" },
  { v: "77.4%", d: "of Malaysian MSMEs are microenterprises, with MSMEs making up 96.2% of all establishments (2025)", s: "SME Corp / DOSM" },
];

export default function Landing() {
  return (
    <>
      <TopBar>
        <a href={REPO} target="_blank" rel="noreferrer">GitHub</a>
        <Link to="/app"><button className="primary">Open demo app</button></Link>
      </TopBar>
      <main className="landing">
        <section className="hero">
          <span className="pill brand">Dormathon 2026 · Track 2 · WorkBuddy Agentic Solutions</span>
          <h1>StartupBuddy</h1>
          <p className="tagline">From idea to first meeting.</p>
          <p className="lead">
            An agentic AI solution that takes aspiring Malaysian founders from a vague business idea to a locally
            validated, council-reviewed business model and their first booked stakeholder meetings, powered by Tencent WorkBuddy.
          </p>
          <div className="cta">
            <Link className="btn primary" to="/app">Open demo app</Link>
            <a className="btn" href={REPO} target="_blank" rel="noreferrer">View the code</a>
            <a className="btn" href={`${REPO}/blob/main/docs/WORKBUDDY_INTEGRATION.md`} target="_blank" rel="noreferrer">Connect WorkBuddy</a>
          </div>
        </section>

        <section className="block">
          <h2>The problem</h2>
          <p className="muted" style={{ maxWidth: 760 }}>
            Young Malaysians who want to start a business get stuck between "I have an idea" and "I'm talking to the
            right people about a validated plan". Generic AI tools write generic plans; help exists but is scattered;
            nobody checks the idea against their real street, and nobody helps them take the first concrete step.
          </p>
          <div className="grid-4" style={{ marginTop: 16 }}>
            {STATS.map((s) => (
              <div className="card stat" key={s.v}><b>{s.v}</b>{s.d}<div className="muted small" style={{ marginTop: 6 }}>Source: {s.s}</div></div>
            ))}
          </div>
        </section>

        <section className="block">
          <h2>How it works: one sentence in, 16 agents at work</h2>
          <div className="grid-4">
            {STEPS.map((s, i) => (
              <div className="card step" key={s.t}><div className="num">{i + 1}</div><h3>{s.t}</h3><p className="muted" style={{ margin: 0 }}>{s.d}</p></div>
            ))}
          </div>
        </section>

        <section className="block">
          <h2>WorkBuddy does real work</h2>
          <div className="card" style={{ padding: 20 }}>
            <p style={{ marginTop: 0 }}>
              StartupBuddy exposes an MCP server that Tencent WorkBuddy connects to. Start a session with one prompt in
              WorkBuddy (<i>"Use StartupBuddy: I want to sell kolo mee near Padungan, Kuching"</i>), then WorkBuddy works through
              StartupBuddy's task queue: desk research, the full report, and relaying your approvals, while the agents
              on Google Cloud build and review the business model.
            </p>
            <p className="muted small" style={{ marginBottom: 0 }}>
              Every figure is labelled <span className="pill ok">sourced</span> <span className="pill info">estimated</span>{" "}
              <span className="pill warn">needs verification</span>. Emails are drafted, never sent automatically.
            </p>
          </div>
        </section>

        <p className="muted small" style={{ marginTop: 48 }}>
          Team SMILING FACE WITH SUNGLASSES: Nathan Yap, Abraham Pang, Malcolm Sim, Zoe Tan · Built with Google ADK, Gemini on Vertex AI, Cloud Run, Firebase and Tencent WorkBuddy.
        </p>
      </main>
    </>
  );
}
