import { useEffect, useRef, useState } from "react";
import { animate, createMotionPath, createDrawable, stagger } from "animejs";
import { reducedMotion } from "./motion";

type NodeDef = { id: string; x: number; y: number; w: number; h: number; label: string; sub: string; group: "user" | "wb" | "run" | "agent" | "data" | "google" };

const NODES: NodeDef[] = [
  { id: "founder", x: 20, y: 40, w: 170, h: 64, label: "Founder", sub: "web app · Firebase", group: "user" },
  { id: "workbuddy", x: 20, y: 400, w: 170, h: 64, label: "Tencent WorkBuddy", sub: "desktop agent + skills", group: "wb" },
  { id: "api", x: 270, y: 40, w: 180, h: 64, label: "FastAPI", sub: "REST + live SSE", group: "run" },
  { id: "mcp", x: 270, y: 400, w: 180, h: 64, label: "MCP server /mcp", sub: "8 tools · API key", group: "run" },
  { id: "queue", x: 270, y: 220, w: 180, h: 64, label: "Task queue", sub: "lease · deadline · retry", group: "run" },
  { id: "coord", x: 530, y: 40, w: 170, h: 56, label: "Problem Coordinator", sub: "1 agent · gate G1", group: "agent" },
  { id: "bmc", x: 530, y: 150, w: 170, h: 56, label: "BMC agents ×9", sub: "3 dependent waves", group: "agent" },
  { id: "council", x: 530, y: 260, w: 170, h: 56, label: "Council ×5", sub: "parallel · code-aggregated", group: "agent" },
  { id: "advisor", x: 530, y: 370, w: 170, h: 56, label: "Advisor", sub: "1 agent · gate G2", group: "agent" },
  { id: "db", x: 790, y: 400, w: 190, h: 64, label: "Cloud SQL Postgres", sub: "sessions · evidence · hybrid search", group: "data" },
  { id: "gemini", x: 790, y: 40, w: 190, h: 56, label: "Gemini 3.5 Flash", sub: "Vertex AI · Google ADK", group: "google" },
  { id: "places", x: 790, y: 150, w: 190, h: 56, label: "Google Places", sub: "nearby competitors", group: "google" },
  { id: "gws", x: 790, y: 260, w: 190, h: 56, label: "Google Workspace", sub: "Calendar + Meet · Gmail drafts", group: "google" },
];

const EXPLAIN: Record<string, { what: string; why: string; status: string }> = {
  founder: { what: "Types one sentence (\"I want to sell kolo mee near Padungan\"), watches 16 agents build the business model live, and approves at two checkpoints.", why: "One prompt, one goal, end-to-end: the founder only answers two yes/no style checkpoints.", status: "Built" },
  workbuddy: { what: "Runs StartupBuddy skills: starts sessions from one prompt, does desk research and writes the report (DOCX), and relays the founder's approvals.", why: "WorkBuddy is a worker in the loop, not a chat window: it pulls real tasks and posts structured results back.", status: "Connector tested (EXP-1/2); skills in testing" },
  api: { what: "Serves the web app: sessions, the live agent event stream (SSE), checkpoints and the report.", why: "Every tool call and handoff is logged and streamed, which is both the canvas animation and the audit trail.", status: "Built · Cloud Run" },
  mcp: { what: "WorkBuddy connects here as a custom MCP connector: start_session, await_next_task, submit_task_result, confirm_gate and more.", why: "MCP lets WorkBuddy call us; every tool answers within 25 s to respect WorkBuddy's time limit.", status: "Built · tested with WorkBuddy 5.7.6" },
  queue: { what: "Agents enqueue tasks for WorkBuddy; WorkBuddy long-polls and claims them. Leases, deadlines and at most 2 attempts.", why: "MCP can't call into WorkBuddy, so the queue lets cloud agents hand work to it. If WorkBuddy is offline, agents continue with a labelled fallback.", status: "Built" },
  coord: { what: "Turns the intent into a grounded problem statement: geocodes the place, counts nearby competitors on Google Maps, searches Malaysian licensing and programmes, merges WorkBuddy desk research.", why: "Grounds the idea in the founder's actual street, not generic advice.", status: "Built" },
  bmc: { what: "Nine agents, one per Business Model Canvas block, in three waves: customers & value first, then channels, relationships, activities, resources, partners, then revenue & costs.", why: "Each wave reads the blocks before it, so the canvas stays consistent, and you can watch it branch out.", status: "Built" },
  council: { what: "A simulated customer, CEO, investor, CFO and mentor score all nine blocks in parallel and list risks and what must be verified.", why: "Plain code, not the model, aggregates the scores into the verdict, so quality control is deterministic.", status: "Built (revision loop next)" },
  advisor: { what: "Turns the agents' decisions into 3–5 first actions (meetings, email drafts), each traced to the agent it came from.", why: "Nothing runs until the founder approves each action at checkpoint G2.", status: "Built" },
  db: { what: "Stores sessions, the canvas, council reviews, the task queue and every labelled evidence item; the knowledge base is searched here.", why: "Hybrid search: full-text ranking today, vector (embedding) search next. Every hit returns its source URL.", status: "Full-text built · vector next" },
  gemini: { what: "All 16 agents run on Gemini 3.5 Flash through Google's Agent Development Kit, with structured outputs.", why: "Structured outputs plus code checks: an unsourced figure is downgraded to 'needs verification' automatically.", status: "Built" },
  places: { what: "Finds real competitors near the founder's location with ratings, review counts and distance.", why: "Evidence with links: e.g. 8 kolo mee stalls within 1 km of Padungan.", status: "Built" },
  gws: { what: "Creates approved Calendar events with Meet links and Gmail drafts in the founder's account.", why: "Emails are drafted, never sent automatically, and only approved actions run.", status: "Built · account linking pending" },
};

const EDGES: [string, string][] = [
  ["founder", "api"], ["workbuddy", "mcp"], ["mcp", "queue"], ["api", "coord"], ["queue", "coord"], ["queue", "council"],
  ["coord", "bmc"], ["bmc", "council"], ["council", "advisor"], ["coord", "gemini"], ["coord", "places"], ["advisor", "gws"],
  ["bmc", "db"], ["advisor", "db"], ["api", "queue"],
];

const center = (n: NodeDef, side: "l" | "r" | "t" | "b") =>
  side === "l" ? [n.x, n.y + n.h / 2] : side === "r" ? [n.x + n.w, n.y + n.h / 2] : side === "t" ? [n.x + n.w / 2, n.y] : [n.x + n.w / 2, n.y + n.h];

function pathFor(a: NodeDef, b: NodeDef) {
  if (Math.abs(a.x - b.x) < 40) {
    const [x1, y1] = a.y < b.y ? center(a, "b") : center(a, "t");
    const [x2, y2] = a.y < b.y ? center(b, "t") : center(b, "b");
    return `M${x1},${y1} C${x1},${(y1 + y2) / 2} ${x2},${(y1 + y2) / 2} ${x2},${y2}`;
  }
  const [x1, y1] = a.x < b.x ? center(a, "r") : center(a, "l");
  const [x2, y2] = a.x < b.x ? center(b, "l") : center(b, "r");
  const mx = (x1 + x2) / 2;
  return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
}

export default function ArchitectureGraph() {
  const root = useRef<SVGSVGElement>(null);
  const [sel, setSel] = useState("workbuddy");
  const byId = Object.fromEntries(NODES.map((n) => [n.id, n]));

  useEffect(() => {
    const svg = root.current;
    if (!svg || reducedMotion()) return;
    const anims: { revert?: () => void; pause?: () => void }[] = [];
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      anims.push(animate(createDrawable(svg.querySelectorAll(".arch-edge")), { draw: ["0 0", "0 1"], duration: 900, delay: stagger(60), ease: "inOutQuad" }));
      anims.push(animate(svg.querySelectorAll(".arch-pop"), { opacity: [0, 1], scale: [0.85, 1], duration: 600, delay: stagger(50, { from: "first" }), ease: "outBack(1.4)" }));
      svg.querySelectorAll<SVGCircleElement>(".arch-packet").forEach((dot, i) => {
        const path = svg.querySelector(`#edge-${dot.dataset.edge}`);
        if (!path) return;
        anims.push(animate(dot, { ...createMotionPath(path), opacity: [0, 1, 1, 0], duration: 2200 + (i % 4) * 300, delay: 1200 + i * 260, loop: true, ease: "inOutSine" }));
      });
    }, { threshold: 0.25 });
    io.observe(svg);
    return () => { io.disconnect(); anims.forEach((a) => a.revert?.()); };
  }, []);

  const info = EXPLAIN[sel];
  const n = byId[sel];
  return (
    <div className="arch">
      <div className="arch-scroll">
      <svg ref={root} viewBox="0 0 1000 490" className="arch-svg" role="img" aria-label="StartupBuddy architecture graph">
        <rect x="255" y="18" width="460" height="462" rx="18" className="arch-zone" />
        <text x="270" y="12" className="arch-zone-label">Google Cloud Run · StartupBuddy API</text>
        <rect x="515" y="26" width="200" height="414" rx="14" className="arch-zone inner" />
        <text x="530" y="452" className="arch-zone-label small">16 ADK agents</text>
        {EDGES.map(([a, b]) => (
          <path key={`${a}-${b}`} id={`edge-${a}-${b}`} d={pathFor(byId[a], byId[b])} className={`arch-edge ${sel === a || sel === b ? "hot" : ""}`} />
        ))}
        {EDGES.map(([a, b]) => (
          <circle key={`p-${a}-${b}`} r="4" className="arch-packet" data-edge={`${a}-${b}`} cx="0" cy="0" opacity="0" />
        ))}
        {NODES.map((d) => (
          <g key={d.id} className={`arch-node g-${d.group} ${sel === d.id ? "sel" : ""}`} transform={`translate(${d.x},${d.y})`}
            onClick={() => setSel(d.id)} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setSel(d.id)} tabIndex={0} role="button" aria-label={d.label}>
            <g className="arch-pop">
              <rect width={d.w} height={d.h} rx="12" />
              <text x="14" y={d.h / 2 - 3} className="t">{d.label}</text>
              <text x="14" y={d.h / 2 + 15} className="s">{d.sub}</text>
            </g>
          </g>
        ))}
      </svg>
      </div>
      <aside className="arch-explain card" aria-live="polite">
        <div className="eyebrow">Click any box · {n.label}</div>
        <h3>{n.label}</h3>
        <p>{info.what}</p>
        <p className="why"><b>Why it matters:</b> {info.why}</p>
        <span className="pill brand">{info.status}</span>
      </aside>
    </div>
  );
}
