"""Factories for the 16 agents. Tools are closures over the session so the model
passes only queries, never data the machine already has (google-adk skill pattern 5)."""
from statistics import mean
from typing import Any

from google.adk.agents import LlmAgent

from app.agent import prompts
from app.agent.common import make_agent
from app.models import BMC_KEYS
from app.rag.search import search as kb_search
from app.schemas.agents import ActionsOut, BlockOut, ProblemOut, ReviewOut
from app.tools.places import nearby_competitors


def knowledge_tool():
    async def search_knowledge(query: str) -> dict:
        """Search StartupBuddy's verified Malaysian knowledge base (licensing, SSM registration,
        funding and support programmes, Sarawak agencies, Business Model Canvas guidance).

        Args:
            query: What to look up, e.g. "food premises licence Kuching" or "TEKUN micro financing".

        Returns:
            {"results": [{"title", "source_url", "publisher", "excerpt"}]}. Cite source_url in evidence.
        """
        return {"results": await kb_search(query, k=4)}

    return search_knowledge


def places_tool(lat: float, lng: float):
    async def find_nearby_places(query: str, radius_m: int = 1000) -> dict:
        """Find businesses near the founder's location on Google Maps.

        Args:
            query: What to search for, e.g. "kolo mee" or "bubble tea".
            radius_m: Search radius in metres (default 1000).

        Returns:
            {"places": [{"name", "rating", "reviews", "distance_km", "maps_url"}]}.
        """
        places = await nearby_competitors(query, lat, lng, radius_m)
        return {"places": places[:12]}

    return find_nearby_places


def coordinator(session_id: str, lat: float | None, lng: float | None) -> LlmAgent:
    tools: list[Any] = [knowledge_tool()]
    if lat is not None and lng is not None:
        tools.append(places_tool(lat, lng))
    return make_agent("problem_coordinator", prompts.COORDINATOR, ProblemOut, session_id, "problem", tools)


def bmc_agent(session_id: str, key: str) -> LlmAgent:
    instr = prompts.BMC_AGENT.format(block_desc=prompts.BMC[key])
    return make_agent(key, instr, BlockOut, session_id, key, [knowledge_tool()])


def council_agent(session_id: str, seat: str) -> LlmAgent:
    instr = prompts.COUNCIL_AGENT.format(seat_desc=prompts.COUNCIL[seat])
    return make_agent(f"council_{seat}", instr, ReviewOut, session_id, f"council_{seat}", [knowledge_tool()])


def advisor(session_id: str) -> LlmAgent:
    return make_agent("advisor", prompts.ADVISOR, ActionsOut, session_id, "advisor", [knowledge_tool()])


def aggregate(reviews: list[ReviewOut]) -> dict[str, Any]:
    """Deterministic council aggregation (docs/AGENTS.md): code, not LLM, decides."""
    per_block: dict[str, list[int]] = {k: [] for k in BMC_KEYS}
    for r in reviews:
        for s in r.scores:
            per_block[s.block].append(s.score)
    means = {k: round(mean(v), 2) if v else None for k, v in per_block.items()}
    to_revise = [k for k, m in means.items() if m is not None and m < 3.0]
    votes = [r.verdict for r in reviews]
    top = max(set(votes), key=votes.count) if votes else "revise"
    if votes.count(top) * 2 <= len(votes):
        top = "revise"
    return {"block_means": means, "blocks_to_revise": to_revise, "overall": top}
