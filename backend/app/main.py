"""StartupBuddy API: REST + SSE for the web app, /mcp for WorkBuddy."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.config import settings
from app.db import SessionLocal, engine
from app.mcp import gws
from app.mcp.workbuddy_server import mcp_http_app, require_api_key, server as mcp_server
from app.models import MIGRATIONS, Base, DemoUser
from app.rag.search import ingest_all
from app.routers import sessions
from app.workbuddy import queue

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("startupbuddy")


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in MIGRATIONS:
            await conn.execute(text(stmt))
    async with SessionLocal() as db:
        if not (await db.execute(select(DemoUser).limit(1))).scalar_one_or_none():
            db.add(DemoUser(display_name="Demo Founder", email=None))
            await db.commit()
    try:
        await ingest_all()
    except Exception:
        log.exception("knowledge ingest failed")
    async with mcp_server.session_manager.run():
        log.info("StartupBuddy ready: model=%s location=%s", settings.gemini_model, settings.google_cloud_location)
        yield


api = FastAPI(title="StartupBuddy API", version="0.1.0", lifespan=lifespan)
api.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.frontend_origin.split(",")],
                   allow_methods=["*"], allow_headers=["*"])
api.include_router(sessions.router)


@api.get("/health")
async def health() -> dict:
    db_ok = True
    try:
        async with SessionLocal() as db:
            await db.execute(text("select 1"))
    except Exception:
        db_ok = False
    return {"ok": db_ok, "db": db_ok, "model": settings.gemini_model,
            "workbuddy_online": await queue.worker_online() if db_ok else False,
            "google_workspace_linked": gws.available()}


_mcp = require_api_key(mcp_http_app)


async def app(scope, receive, send):
    """Route /mcp to the WorkBuddy MCP server (API-key gated); everything else to FastAPI."""
    if scope["type"] == "http" and (scope["path"] == "/mcp" or scope["path"].startswith("/mcp/")):
        if scope["path"] != "/mcp":
            scope = dict(scope, path="/mcp")
        await _mcp(scope, receive, send)
        return
    await api(scope, receive, send)
