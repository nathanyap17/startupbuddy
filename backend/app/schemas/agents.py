"""Structured outputs the ADK agents must return (LlmAgent.output_schema)."""
from typing import Literal

from pydantic import BaseModel, Field

Label = Literal["sourced", "estimated", "needs_verification"]


class EvidenceOut(BaseModel):
    claim: str = Field(description="A factual claim, e.g. 'Kolo mee stalls within 1 km'")
    value: str | None = Field(default=None, description="The figure or fact, e.g. '8'")
    label: Label = Field(description="sourced (needs source_url), estimated (needs method), or needs_verification")
    source_url: str | None = Field(default=None, description="URL the fact came from (Google Maps link, knowledge source)")
    method: str | None = Field(default=None, description="How an estimate was calculated")


class ProblemOut(BaseModel):
    statement: str = Field(description="One-paragraph problem statement grounded in the location")
    target_user: str
    pain: str
    why_now: str
    demand_signals: list[str] = Field(default_factory=list)
    competition_summary: str = ""
    differentiation_hypothesis: str = ""
    evidence: list[EvidenceOut] = Field(default_factory=list)


class BlockOut(BaseModel):
    summary: str = Field(description="2-3 sentence summary of this canvas block")
    items: list[str] = Field(description="3-6 concrete bullet points for this block")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions that must be tested")
    evidence: list[EvidenceOut] = Field(default_factory=list)


class BlockScore(BaseModel):
    block: Literal["customer_segments", "value_propositions", "channels", "customer_relationships",
                   "key_activities", "key_resources", "key_partners", "revenue_streams", "cost_structure"]
    score: int = Field(ge=1, le=5, description="1 = weak, 5 = strong")


class ReviewOut(BaseModel):
    scores: list[BlockScore] = Field(description="One score for each of the 9 blocks")
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    must_verify: list[str] = Field(default_factory=list, description="Claims the founder must verify in the real world")
    improve: list[str] = Field(default_factory=list, description="Concrete improvements")
    verdict: Literal["go", "revise", "stop"]


class ActionOut(BaseModel):
    kind: Literal["calendar_event", "gmail_draft"]
    title: str
    rationale: str = Field(description="Why, citing which agent's decision this comes from")
    source_agent: str = Field(description="Agent whose decision produced this action, e.g. key_partners")
    start_iso: str | None = Field(default=None, description="For calendar_event: start time ISO 8601 with +08:00")
    duration_min: int = 45
    location: str = ""
    email_to: str = Field(default="", description="For gmail_draft: an organisation's public contact address, or empty for the founder to fill")
    email_subject: str = ""
    email_body: str = ""


class ActionsOut(BaseModel):
    actions: list[ActionOut] = Field(description="3-5 concrete first actions")
    next_30_days: list[str] = Field(default_factory=list)
