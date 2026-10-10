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
    kind: Literal["email_outreach", "site_visit", "online_meeting", "task"] = Field(
        description="email_outreach: draft an email to an organisation and wait for its reply; site_visit: an in-person "
                    "visit or meet-up at a physical place (no video link); online_meeting: a video call, only when the "
                    "other side is remote or it is naturally online; task: something the founder does alone (no Google action)")
    title: str
    rationale: str = Field(description="Why, citing which agent's decision this comes from")
    source_agent: str = Field(description="Agent whose decision produced this action, e.g. key_partners")
    start_iso: str | None = Field(default=None, description="site_visit/online_meeting: start time ISO 8601 with +08:00")
    duration_min: int = 45
    location: str = Field(default="", description="site_visit: the physical address or place name")
    email_to: str = Field(default="", description="email_outreach: an organisation's public contact address, or empty for the founder to fill")
    email_subject: str = ""
    email_body: str = Field(default="", description="email_outreach: polite, specific, under 150 words, asks for a meeting or information")
    follow_up_plan: str = Field(default="", description="What happens next, e.g. 'wait for reply, then schedule the meeting'")


class ActionsOut(BaseModel):
    actions: list[ActionOut] = Field(description="3-5 concrete first actions")
    next_30_days: list[str] = Field(default_factory=list)


class PilotSummaryOut(BaseModel):
    one_liner: str
    verdict: Literal["go", "revise", "stop"]
    highlights: list[str] = Field(default_factory=list)
    first_step: str = ""


class ScreenOut(BaseModel):
    verdict: Literal["allowed", "regulated", "ambiguous", "prohibited"]
    interpretation: str = Field(description="What the founder most likely means, in one sentence, without assuming the benign reading of ambiguous words")
    business_type: Literal["physical", "digital", "hybrid"] = Field(description="physical: serves customers at a place; digital: sold/delivered online; hybrid: both")
    sector: str
    needs_location_scouting: bool = Field(description="True only if nearby physical competitors and foot traffic matter")
    competitor_query: str = Field(default="", description="Short Google Maps query for nearby competitors, e.g. 'kolo mee' (physical/hybrid only)")
    online_competitor_hints: list[str] = Field(default_factory=list, description="Kinds of online competitors/platforms to research (digital/hybrid)")
    regulators: list[str] = Field(default_factory=list, description="Malaysian regulators/agencies involved")
    licences: list[str] = Field(default_factory=list, description="Licences, permits or laws that apply")
    critical_concerns: list[str] = Field(default_factory=list, description="Honest early red flags about viability or legality")
    clarifying_question: str = Field(default="", description="For ambiguous: ONE friendly question that resolves the ambiguity")
    refusal_reason: str = Field(default="", description="For prohibited: why, citing the law, in plain words")
    legal_alternatives: list[str] = Field(default_factory=list, description="For prohibited/ambiguous: legal business ideas close to the intent")


class FollowUpOut(BaseModel):
    reply_summary: str = Field(description="One or two sentences: what the other side said")
    proposes_time: bool = Field(description="True only if the reply proposes or confirms a specific date and time")
    start_iso: str | None = Field(default=None, description="Proposed start, ISO 8601 with +08:00")
    duration_min: int = 45
    is_online: bool = Field(default=False, description="True only if the reply says the meeting is online / video call / Google Meet / Zoom")
    location: str = ""
    suggested_next_step: str = Field(description="What the founder should do next, e.g. reply to confirm, prepare documents")
