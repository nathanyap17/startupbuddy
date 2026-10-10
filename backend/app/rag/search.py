"""Knowledge base: ingest knowledge/**/*.md and search.

Pilot: Postgres full-text search (ts_rank). Vector half of hybrid search (EmbeddingGemma /
Vertex) is post-pilot (PLAN.md pilot scope). Every hit returns its source_url."""
import logging
import re
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select, text

from app.config import settings
from app.db import SessionLocal
from app.models import KbChunk, KbDocument

log = logging.getLogger("startupbuddy.rag")
FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def _parse(md: str) -> tuple[dict[str, str], str]:
    m = FRONT.match(md)
    meta: dict[str, str] = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.split("#")[0].strip() if k.strip() != "source_url" else v.strip()
        md = md[m.end():]
    return meta, md


def _chunks(body: str, size: int = 900) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) > size and cur:
            out.append(cur)
            cur = ""
        cur = f"{cur}\n\n{p}" if cur else p
    if cur:
        out.append(cur)
    return out


async def ingest_all() -> int:
    root = Path(settings.knowledge_dir)
    files = [p for p in root.rglob("*.md") if p.name.lower() != "readme.md"]
    n = 0
    async with SessionLocal() as db:
        for f in files:
            meta, body = _parse(f.read_text(encoding="utf-8"))
            if not meta.get("source_url"):
                log.warning("skip %s: no source_url", f)
                continue
            rel = str(f.relative_to(root)).replace("\\", "/")
            await db.execute(delete(KbDocument).where(KbDocument.path == rel))
            doc = KbDocument(namespace=meta.get("namespace", rel.split("/")[0]), title=meta.get("title", f.stem),
                             source_url=meta["source_url"], publisher=meta.get("publisher", ""),
                             retrieved_on=meta.get("retrieved_on", ""), path=rel)
            db.add(doc)
            await db.flush()
            for i, c in enumerate(_chunks(body)):
                db.add(KbChunk(document_id=doc.id, ordinal=i, text=f"{doc.title}\n{c}"))
            n += 1
        await db.commit()
    log.info("knowledge ingested: %d documents", n)
    return n


async def search(query: str, k: int = 5, namespace: str | None = None) -> list[dict[str, Any]]:
    sql = """
        SELECT d.title, d.source_url, d.publisher, d.namespace, c.text,
               ts_rank(c.tsv, websearch_to_tsquery('english', :q)) AS score
        FROM kb_chunk c JOIN kb_document d ON d.id = c.document_id
        WHERE c.tsv @@ websearch_to_tsquery('english', :q) {ns}
        ORDER BY score DESC LIMIT :k"""
    params: dict[str, Any] = {"q": query, "k": k}
    ns = ""
    if namespace:
        ns, params["ns"] = "AND d.namespace = :ns", namespace
    async with SessionLocal() as db:
        rows = (await db.execute(text(sql.format(ns=ns)), params)).mappings().all()
        if not rows:  # fall back to OR-of-words for short/odd queries
            words = " OR ".join(w for w in re.findall(r"\w{3,}", query)[:8])
            if words:
                params["q"] = words
                rows = (await db.execute(text(sql.format(ns=ns)), params)).mappings().all()
    return [{"title": r["title"], "source_url": r["source_url"], "publisher": r["publisher"],
             "namespace": r["namespace"], "excerpt": r["text"][:700]} for r in rows]
