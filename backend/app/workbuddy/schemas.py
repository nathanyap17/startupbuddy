"""Output schemas WorkBuddy task skills must return (sent as JSON Schema in output_schema)."""
from typing import Literal

from pydantic import BaseModel, Field


class Fact(BaseModel):
    claim: str
    value: str | None = None
    label: Literal["sourced", "estimated", "needs_verification"]
    source_url: str | None = None
    method: str | None = None


class Competitor(BaseModel):
    name: str
    note: str = ""
    source_url: str | None = None


class DeskResearchResult(BaseModel):
    findings: list[Fact] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    regulations: list[Fact] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class ReportBuilderResult(BaseModel):
    title: str
    summary: str = Field(description="5-sentence executive summary")
    report_markdown: str = Field(description="The polished full report in Markdown (all sections)")
    local_file_paths: list[str] = Field(default_factory=list, description="Paths of DOCX/PDF files saved on the WorkBuddy machine")
    file_urls: list[str] = Field(default_factory=list, description="URLs returned by upload_artifact, if used")


SKILL_SCHEMAS: dict[str, type[BaseModel]] = {
    "desk_research": DeskResearchResult,
    "report_builder": ReportBuilderResult,
}
