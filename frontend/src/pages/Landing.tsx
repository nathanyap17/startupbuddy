import { CSSProperties, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { animate, createDrawable, createTimeline, splitText, stagger } from "animejs";
import TopBar from "../components/TopBar";
import "./landing.css";
import ArchitectureGraph from "../components/ArchitectureGraph";
import { reducedMotion, useReveal, useScrollReveal } from "../components/motion";

/** Stagger index for the reversible scroll reveal (.rv). */
const rvd = (i: number) => ({ "--d": i }) as CSSProperties;

const REPO = "https://github.com/nathanyap17/startupbuddy";

const LADDER = [
  { t: "Shape the idea", d: "Turn one sentence into a grounded problem statement" },
  { t: "Validate locally", d: "Competitors on Google Maps, Malaysian licences and programmes" },
  { t: "Council review", d: "Customer, CEO, investor, CFO and mentor pressure-test the model" },
  { t: "First meeting booked", d: "Approved meetings and email drafts land in your Google account" },
];

const STATS = [
  { n: 1.7, fmt: (v: number) => `${v.toFixed(1)}%`, d: "of Malaysian public-university graduates were self-employed (2013 tracer study; 1.4% in 2010)", s: "UNIMAS IJBS; HRMARS" },
  { n: 6, fmt: (v: number) => `${Math.round(v)}%`, d: "of youth entrepreneurs obtain financing from financial institutions (KRI, cited)", s: "IIUM repository" },
  { n: 77.4, fmt: (v: number) => `${v.toFixed(1)}%`, d: "of Malaysian MSMEs are microenterprises; MSMEs are 96.2% of all establishments (2025)", s: "SME Corp / DOSM" },
];

const STORY = [
  ["The idea stays vague", "Who exactly buys, at what price, and why from her rather than the stalls already there?"],
  ["The market is judged by gut feel", "No quick way to see competitors within walking distance, their ratings, or who lives and works nearby."],
  ["Generic AI, generic answers", "A tidy plan that would read the same for Kuala Lumpur or Jakarta, blind to her street and council rules."],
  ["Help is scattered", "SSM, the local council, food handler training, TEKUN, SME Corp, MYStartup: separate sites, unclear which apply."],
  ["Nobody challenges the plan", "No mentor or investor to say \"your price won't cover your rent\"."],
  ["The first step never happens", "No meeting booked, no email sent. The idea quietly dies, or launches unprepared."],
];

const PHASES = [
  { k: "01", t: "Ground", d: "Problem Coordinator + Google Maps + knowledge base + WorkBuddy desk research", gate: "G1 · you confirm the problem" },
  { k: "02", t: "Build", d: "9 canvas agents in 3 dependent waves: 2 → 5 → 2", gate: "" },
  { k: "03", t: "Challenge", d: "5-seat council scores every block; code aggregates the verdict; WorkBuddy writes the report", gate: "" },
  { k: "04", t: "Act", d: "Advisor proposes meetings and email drafts traced to agent decisions", gate: "G2 · you approve each action" },
];

const HARNESS = [
  ["Two human checkpoints", "Agents pause for the founder at G1 (problem) and G2 (actions). Nothing outward happens without approval."],
  ["Every figure is labelled", "sourced (with link), estimated (with method) or needs verification, enforced by database constraints, not prompts."],
  ["Drafts, never sends", "Gmail actions create drafts only. Calendar events are created only for approved actions."],
  ["Bounded everything", "Each agent turn has a timeout; WorkBuddy tasks have leases, deadlines and at most 2 attempts; tools answer within 25 s."],
  ["Graceful fallbacks", "If WorkBuddy is offline, agents continue with a visible, labelled fallback instead of hanging the run."],
  ["Full audit trail", "Every tool call, handoff and latency is logged and streamed. It's the live canvas and the evidence."],
];

const TICKER = [
  "problem_coordinator · Google Maps: 8 'kolo mee' competitors within 1 km",
  "workbuddy · picked up desk_research",
  "value_propositions · differentiating against Annie Kolo Mee (4.3★, 171 reviews)",
  "council_cfo · checking unit economics against rent in RM",
  "council · verdict REVISE · weakest block: key_resources",
  "advisor · proposed: Visit MBKS licensing counter (from key_activities)",
];

function Hero() {
  const root = useRef<HTMLElement>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const el = root.current;
    if (!el || reducedMotion()) return;
    const split = splitText(el.querySelector("h1")!, { words: { wrap: "clip" } });
    const tl = createTimeline({ defaults: { ease: "outExpo" } })
      .add(el.querySelector(".hero-brand")!, { opacity: [0, 1], x: [-16, 0], duration: 700 })
      .add(split.words, { y: ["110%", "0%"], duration: 900, delay: stagger(70) }, "-=400")
      .add(el.querySelectorAll(".hero-fade"), { opacity: [0, 1], y: [14, 0], duration: 700, delay: stagger(90) }, "-=600")
      .add(el.querySelectorAll(".rung"), { opacity: [0, 1], x: [40, 0], duration: 800, delay: stagger(120) }, "-=900")
      .add(el.querySelector(".rung.dark")!, { scale: [1, 1.03, 1], duration: 900, ease: "inOutSine" });
    const glow = animate(el.querySelectorAll(".orbit-dot"), {
      rotate: "1turn", duration: 24000, loop: true, ease: "linear", delay: stagger(-1500),
    });
    return () => { tl.revert(); glow.revert(); split.revert(); };
  }, []);
  useEffect(() => {
    const t = setInterval(() => setTick((x) => (x + 1) % TICKER.length), 2600);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (reducedMotion()) return;
    const a = animate(".ticker-line", { opacity: [0, 1], y: [8, 0], duration: 500, ease: "outQuad" });
    return () => { a.revert(); };
  }, [tick]);

  return (
    <section className="hero" ref={root}>
      <div>
        <div className="hero-brand"><img src="/logo.png" alt="" /><span>StartupBuddy</span></div>
        <h1>From idea to first meeting.</h1>
        <p className="lead hero-fade">
          An agentic AI solution that takes aspiring Malaysian founders from a vague business idea to a locally
          validated, council-reviewed business model and their first booked stakeholder meetings, powered by Tencent WorkBuddy.
        </p>
        <div className="cta hero-fade">
          <Link className="btn primary" to="/app">Open demo app</Link>
          <a className="btn" href="#architecture">See how it works</a>
          <a className="btn" href={REPO} target="_blank" rel="noreferrer">View the code</a>
        </div>
        <div className="ticker hero-fade" aria-live="off">
          <span className="ticker-label">Sample run · kolo mee @ Padungan</span>
          <span className="ticker-line" key={tick}>{TICKER[tick]}</span>
        </div>
        <div className="powered hero-fade">Powered by Tencent WorkBuddy</div>
      </div>
      <div className="hero-right">
        <div className="orbit" aria-hidden="true">
          {Array.from({ length: 16 }).map((_, i) => (
            <span key={i} className="orbit-dot" style={{ transform: `rotate(${(i * 360) / 16}deg)` }}><i /></span>
          ))}
        </div>
        <div className="ladder">
          {LADDER.map((r, i) => (
            <div key={r.t} className={`rung ${i === LADDER.length - 1 ? "dark" : ""}`}>
              <div className="n">{String(i + 1).padStart(2, "0")}</div>
              <div><b>{r.t}</b><span>{r.d}</span></div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Problem() {
  const ref = useReveal<HTMLElement>((el) => {
    const nums = el.querySelectorAll<HTMLElement>(".stat b");
    const anims = STATS.map((s, i) => {
      const o = { v: 0 };
      return animate(o, { v: s.n, duration: 1600, delay: i * 150, ease: "outExpo", onUpdate: () => { nums[i].textContent = s.fmt(o.v); } });
    });
    const line = animate(createDrawable(el.querySelectorAll(".story-line")), { draw: ["0 0", "0 1"], duration: 1600, ease: "inOutQuad", delay: 300 });
    return () => { anims.forEach((x) => x.revert()); line.revert(); };
  });
  return (
    <section className="block" ref={ref} id="problem">
      <div className="eyebrow rv">The problem</div>
      <h2 className="rv" style={rvd(1)}>Ideas stall before the first real conversation</h2>
      <p className="muted section-lead rv" style={rvd(2)}>
        Young Malaysians who want to start a business get stuck between "I have an idea" and "I'm talking to the right
        people about a validated plan". They don't lack app builders; they lack local validation and a path to the right people.
      </p>
      <div className="grid-3">
        {STATS.map((s, i) => (
          <div className="card stat rv" style={rvd(i)} key={s.s}><b>{s.fmt(s.n)}</b>{s.d}<div className="muted small" style={{ marginTop: 8 }}>Source: {s.s}</div></div>
        ))}
      </div>
      <h3 className="story-h rv">What happens today: a student in Kuching wants to sell kolo mee near Padungan</h3>
      <div className="story">
        <svg className="story-svg" viewBox="0 0 1000 8" preserveAspectRatio="none" aria-hidden="true"><path className="story-line" d="M0,4 L1000,4" /></svg>
        {STORY.map(([t, d], i) => (
          <div className="story-step rv" style={rvd(i)} key={t}><div className="story-n">{i + 1}</div><b>{t}</b><span>{d}</span></div>
        ))}
      </div>
    </section>
  );
}

function Workflow() {
  const ref = useReveal<HTMLElement>((el) => {
    const tl = createTimeline({ defaults: { ease: "outQuart" } })
      .add(createDrawable(el.querySelectorAll(".flow-line")), { draw: ["0 0", "0 1"], duration: 1400, ease: "inOutQuad" })
      .add(el.querySelectorAll(".wave-dot"), { scale: [0, 1], duration: 400, delay: stagger(60), ease: "outBack(2)" }, 400);
    const pulse = animate(el.querySelectorAll(".wave-dot"), { opacity: [1, 0.45, 1], duration: 1800, delay: stagger(120), loop: true, ease: "inOutSine" });
    return () => { tl.revert(); pulse.revert(); };
  });
  return (
    <section className="block" ref={ref} id="workflow">
      <div className="eyebrow rv">The solution · workflow</div>
      <h2 className="rv" style={rvd(1)}>One sentence in. Four phases. Two checkpoints.</h2>
      <p className="muted section-lead rv" style={rvd(2)}>The founder types one goal; agents plan, execute, collaborate and validate, and only stop where a human decision belongs.</p>
      <div className="flow">
        <svg className="flow-svg" viewBox="0 0 1000 10" preserveAspectRatio="none" aria-hidden="true"><path className="flow-line" d="M0,5 L1000,5" /></svg>
        {PHASES.map((p, i) => (
          <div className="phase card rv" style={rvd(i)} key={p.k}>
            <div className="phase-k">{p.k}</div>
            <h3>{p.t}</h3>
            <p className="muted">{p.d}</p>
            {i === 1 && (
              <div className="waves" aria-label="Waves of 2, 5 and 2 agents">
                {[2, 5, 2].map((n, w) => <div className="wave" key={w}>{Array.from({ length: n }).map((_, j) => <span className="wave-dot" key={j} />)}</div>)}
              </div>
            )}
            {i === 2 && (
              <div className="waves" aria-label="Five council seats">
                <div className="wave">{["Cu", "CEO", "Inv", "CFO", "Me"].map((s) => <span className="wave-dot seat" key={s}>{s}</span>)}</div>
              </div>
            )}
            {p.gate && <span className="gate-chip">⏸ {p.gate}</span>}
          </div>
        ))}
      </div>
    </section>
  );
}

function Harness() {
  return (
    <section className="block" id="harness">
      <div className="eyebrow rv">The harness</div>
      <h2 className="rv" style={rvd(1)}>Guardrails that make the agents trustworthy</h2>
      <p className="muted section-lead rv" style={rvd(2)}>Autonomy where it helps, code-enforced limits where it matters.</p>
      <div className="grid-3">
        {HARNESS.map(([t, d], i) => (
          <div className="card harness-card rv rv-tilt" style={rvd(i)} key={t}><div className="h-idx">{String(i + 1).padStart(2, "0")}</div><h3>{t}</h3><p className="muted">{d}</p></div>
        ))}
      </div>
    </section>
  );
}

function Architecture() {
  return (
    <section className="block" id="architecture">
      <div className="eyebrow rv">Architecture · click to explore</div>
      <h2 className="rv" style={rvd(1)}>16 agents on Google Cloud, WorkBuddy in the loop</h2>
      <p className="muted section-lead rv" style={rvd(2)}>
        Agents run on Cloud Run with Google ADK and Gemini. WorkBuddy connects over MCP and pulls work from a task queue.
        Knowledge is retrieved with hybrid search (full-text today, vector next). Click any box to see what it does.
      </p>
      <div className="rv" style={rvd(3)}><ArchitectureGraph /></div>
    </section>
  );
}

function ClosingCta() {
  const ref = useReveal<HTMLElement>((el) => {
    const b = animate(el.querySelectorAll(".closing-glow"), { scale: [0.9, 1.08], opacity: [0.5, 0.9], duration: 2400, loop: true, alternate: true, ease: "inOutSine" });
    return () => { b.revert(); };
  });
  return (
    <section className="block closing card rv" ref={ref}>
      <span className="closing-glow" aria-hidden="true" />
      <div className="eyebrow" style={{ color: "var(--brand-dim)" }}>Try it</div>
      <h2>Bring one sentence. Leave with a plan and a meeting.</h2>
      <p>Start in the web app or in WorkBuddy: <i>"Use StartupBuddy: I want to sell kolo mee near Padungan, Kuching."</i></p>
      <div className="cta">
        <Link className="btn light" to="/app">Open demo app</Link>
        <a className="btn outline-light" href={`${REPO}/blob/main/docs/WORKBUDDY_INTEGRATION.md`} target="_blank" rel="noreferrer">Connect WorkBuddy</a>
      </div>
    </section>
  );
}

export default function Landing() {
  const main = useRef<HTMLElement>(null);
  useScrollReveal(main);
  return (
    <>
      <TopBar glass>
        <a className="hide-sm" href="#workflow">Workflow</a>
        <a className="hide-sm" href="#architecture">Architecture</a>
        <a className="hide-sm" href={REPO} target="_blank" rel="noreferrer">GitHub</a>
        <Link to="/app"><button className="primary">Open demo app</button></Link>
      </TopBar>
      <main className="landing" ref={main}>
        <Hero />
        <Problem />
        <Workflow />
        <Harness />
        <Architecture />
        <ClosingCta />
        <footer className="footer rv">
          <div className="footer-brand"><img src="/logo.png" alt="" /><b>StartupBuddy</b><span className="muted">From idea to first meeting.</span></div>
          <div className="muted small">
            Team SMILING FACE WITH SUNGLASSES: Nathan Yap, Abraham Pang, Malcolm Sim, Zoe Tan · Dormathon 2026, Track 2: WorkBuddy Agentic Solutions<br />
            Built with Google ADK, Gemini on Vertex AI, Cloud Run, Cloud SQL, Firebase and Tencent WorkBuddy · <a href={REPO} target="_blank" rel="noreferrer">GitHub</a>
          </div>
        </footer>
      </main>
    </>
  );
}
