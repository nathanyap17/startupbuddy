import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { marked } from "marked";
import TopBar from "../components/TopBar";
import { api, SessionDetail } from "../api";

// Report text comes from LLMs and web research: drop any raw HTML before rendering.
marked.use({ renderer: { html: () => "" } });

export default function Report() {
  const { id = "" } = useParams();
  const [md, setMd] = useState("");
  const [d, setD] = useState<SessionDetail | null>(null);
  useEffect(() => { api.report(id).then(setMd); api.get(id).then(setD); }, [id]);
  const wb = d?.workbuddy_tasks.find((t) => t.skill === "report_builder" && t.status === "succeeded")?.result;
  const download = () => {
    const url = URL.createObjectURL(new Blob([wb?.report_markdown || md], { type: "text/markdown" }));
    Object.assign(document.createElement("a"), { href: url, download: `startupbuddy-${id}.md` }).click();
  };
  return (
    <>
      <TopBar>
        <button onClick={download}>Download .md</button>
        <Link to={`/app/s/${id}`}><button className="ghost">Back to canvas</button></Link>
      </TopBar>
      <main className="report">
        {wb && (
          <div className="card" style={{ padding: 14, marginBottom: 16 }}>
            <span className="pill info">Built by Tencent WorkBuddy</span> <b>{wb.title}</b>
            <p className="small" style={{ marginBottom: 0 }}>{wb.summary}</p>
            {wb.local_file_paths?.length ? <p className="small muted" style={{ margin: 0 }}>Files saved by WorkBuddy: {wb.local_file_paths.join(", ")}</p> : null}
          </div>
        )}
        {d?.artifacts.map((a) => <p key={a.id}><a href={a.url}>⬇ {a.filename}</a></p>)}
        <div dangerouslySetInnerHTML={{ __html: marked.parse(wb?.report_markdown || md) as string }} />
      </main>
    </>
  );
}
