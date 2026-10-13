"""SQLAlchemy models. Mirrors docs/DATA_MODEL.md (pilot: create_all, no Alembic yet)."""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.schema import Computed

from app.ids import new_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def pk() -> Mapped[str]:
    return mapped_column(String(26), primary_key=True, default=new_id)


def ts(nullable: bool = False) -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=nullable, default=None if nullable else utcnow)


def fk_session() -> Mapped[str]:
    return mapped_column(String(26), ForeignKey("startup_session.id", ondelete="CASCADE"), index=True)


SESSION_PHASES = ("intake", "screening", "gate_g0", "blocked", "problem", "gate_g1", "bmc", "council", "deliverables", "advisor",
                  "gate_g2", "actions", "done", "failed")
BMC_KEYS = ("customer_segments", "value_propositions", "channels", "customer_relationships",
            "key_activities", "key_resources", "key_partners", "revenue_streams", "cost_structure")
COUNCIL_SEATS = ("customer", "ceo", "investor", "cfo", "mentor")
EVIDENCE_LABELS = ("sourced", "estimated", "needs_verification")


class DemoUser(Base):
    __tablename__ = "demo_user"
    id: Mapped[str] = pk()
    display_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = ts()


class StartupSession(Base):
    __tablename__ = "startup_session"
    id: Mapped[str] = pk()
    user_id: Mapped[str] = mapped_column(String(26), ForeignKey("demo_user.id"))
    title: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(Text)
    location_text: Mapped[str] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lng: Mapped[float | None] = mapped_column(nullable=True)
    phase: Mapped[str] = mapped_column(String(20), default="intake")
    revision_round: Mapped[int] = mapped_column(Integer, default=0)
    origin: Mapped[str] = mapped_column(String(20), default="web")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_g1: Mapped[bool] = mapped_column(default=False)  # "Always allow" chosen by the founder
    auto_g2: Mapped[bool] = mapped_column(default=False)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # pilot summary at the end
    screen: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # Phase 0 intake screening
    clarification: Mapped[str | None] = mapped_column(Text, nullable=True)  # founder's answer at G0
    created_at: Mapped[datetime] = ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_message"
    id: Mapped[str] = pk()
    session_id: Mapped[str] = fk_session()
    role: Mapped[str] = mapped_column(String(12))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(12), default="web")  # web | workbuddy
    created_at: Mapped[datetime] = ts()


# Idempotent column additions for databases created before these fields existed (pilot: no Alembic).
MIGRATIONS = [
    "ALTER TABLE startup_session ADD COLUMN IF NOT EXISTS auto_g1 boolean NOT NULL DEFAULT false",
    "ALTER TABLE startup_session ADD COLUMN IF NOT EXISTS auto_g2 boolean NOT NULL DEFAULT false",
    "ALTER TABLE startup_session ADD COLUMN IF NOT EXISTS summary jsonb",
    "ALTER TABLE startup_session ADD COLUMN IF NOT EXISTS screen jsonb",
    "ALTER TABLE startup_session ADD COLUMN IF NOT EXISTS clarification text",
    "ALTER TABLE action_item ADD COLUMN IF NOT EXISTS follow_up varchar(20)",
    "ALTER TABLE action_item ADD COLUMN IF NOT EXISTS thread_id text",
    "ALTER TABLE action_item ADD COLUMN IF NOT EXISTS follow_up_note text",
    "ALTER TABLE action_item ADD COLUMN IF NOT EXISTS follow_up_at timestamptz",
    "ALTER TABLE bmc_block ADD COLUMN IF NOT EXISTS instruction text",
    "ALTER TABLE bmc_block ADD COLUMN IF NOT EXISTS change_note text",
    "ALTER TABLE bmc_block ADD COLUMN IF NOT EXISTS stale_reason text",
    "ALTER TABLE council_verdict ADD COLUMN IF NOT EXISTS trigger text",
]


class ProblemStatement(Base):
    __tablename__ = "problem_statement"
    id: Mapped[str] = pk()
    session_id: Mapped[str] = fk_session()
    version: Mapped[int] = mapped_column(Integer, default=1)
    statement: Mapped[str] = mapped_column(Text)
    target_user: Mapped[str] = mapped_column(Text, default="")
    pain: Mapped[str] = mapped_column(Text, default="")
    why_now: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    confirmed_at: Mapped[datetime | None] = ts(nullable=True)
    created_at: Mapped[datetime] = ts()


class EvidenceItem(Base):
    __tablename__ = "evidence_item"
    __table_args__ = (
        CheckConstraint("label IN ('sourced','estimated','needs_verification')", name="ck_evidence_label"),
        CheckConstraint("label <> 'sourced' OR source_url IS NOT NULL", name="ck_sourced_has_url"),
        CheckConstraint("label <> 'estimated' OR method IS NOT NULL", name="ck_estimated_has_method"),
    )
    id: Mapped[str] = pk()
    session_id: Mapped[str] = fk_session()
    scope: Mapped[str] = mapped_column(String(40))
    claim: Mapped[str] = mapped_column(Text)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str] = mapped_column(String(20))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str | None] = mapped_column(Text, nullable=True)
    produced_by: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = ts()


class BmcBlock(Base):
    __tablename__ = "bmc_block"
    __table_args__ = (UniqueConstraint("session_id", "key", "round"),)
    id: Mapped[str] = pk()
    session_id: Mapped[str] = fk_session()
    key: Mapped[str] = mapped_column(String(40))
    round: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)  # founder's @-refinement that produced this version
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)  # agent's one-line "what changed"
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # an upstream block changed after this version
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CouncilReview(Base):
    __tablename__ = "council_review"
    id: Mapped[str] = pk()
    session_id: Mapped[str] = fk_session()
    seat: Mapped[str] = mapped_column(String(20))
    round: Mapped[int] = mapped_column(Integer, default=0)
    scores: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    strengths: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    risks: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    must_verify: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    improve: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    verdict: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = ts()


class CouncilVerdict(Base):
    __tablename__ = "council_verdict"
    id: Mapped[str] = pk()
    session_id: Mapped[str] = fk_session()
    round: Mapped[int] = mapped_column(Integer, default=0)
    block_means: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    blocks_to_revise: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    overall: Mapped[str] = mapped_column(String(10))
    trigger: Mapped[str | None] = mapped_column(Text, nullable=True)  # what produced this round (initial / founder refinement)
    created_at: Mapped[datetime] = ts()


class WorkbuddyTask(Base):
    __tablename__ = "workbuddy_task"
    __table_args__ = (Index("ix_wbt_status_created", "status", "created_at"),)
    id: Mapped[str] = pk()
    session_id: Mapped[str] = fk_session()
    skill: Mapped[str] = mapped_column(String(40))
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="queued")
    worker_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_until: Mapped[datetime | None] = ts(nullable=True)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = ts()
    claimed_at: Mapped[datetime | None] = ts(nullable=True)
    finished_at: Mapped[datetime | None] = ts(nullable=True)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeat"
    worker_id: Mapped[str] = mapped_column(Text, primary_key=True)
    last_seen: Mapped[datetime] = ts()


class Artifact(Base):
    __tablename__ = "artifact"
    id: Mapped[str] = pk()
    session_id: Mapped[str] = fk_session()
    task_id: Mapped[str | None] = mapped_column(String(26), nullable=True)
    kind: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)
    created_at: Mapped[datetime] = ts()


class ActionItem(Base):
    __tablename__ = "action_item"
    id: Mapped[str] = pk()
    session_id: Mapped[str] = fk_session()
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    source_agent: Mapped[str] = mapped_column(String(60))
    approval: Mapped[str] = mapped_column(String(12), default="pending")
    decided_at: Mapped[datetime | None] = ts(nullable=True)
    executed_at: Mapped[datetime | None] = ts(nullable=True)
    external_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # follow-up lifecycle: waiting_reply -> replied | scheduled; site visits: awaiting_update -> done | reschedule
    follow_up: Mapped[str | None] = mapped_column(String(20), nullable=True)
    thread_id: Mapped[str | None] = mapped_column(Text, nullable=True)  # Gmail thread of an email_outreach draft
    follow_up_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_at: Mapped[datetime | None] = ts(nullable=True)
    created_at: Mapped[datetime] = ts()


class AgentEvent(Base):
    __tablename__ = "agent_event"
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = fk_session()
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    agent: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(20))
    target: Mapped[str | None] = mapped_column(String(60), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class KbDocument(Base):
    __tablename__ = "kb_document"
    id: Mapped[str] = pk()
    namespace: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(Text, default="")
    retrieved_on: Mapped[str] = mapped_column(String(10), default="")
    path: Mapped[str] = mapped_column(Text, unique=True)


class KbChunk(Base):
    __tablename__ = "kb_chunk"
    __table_args__ = (Index("ix_kb_chunk_tsv", "tsv", postgresql_using="gin"),)
    id: Mapped[str] = pk()
    document_id: Mapped[str] = mapped_column(String(26), ForeignKey("kb_document.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    tsv: Mapped[Any] = mapped_column(TSVECTOR, Computed("to_tsvector('english', text)", persisted=True))
