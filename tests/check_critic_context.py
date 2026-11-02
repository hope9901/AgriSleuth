"""Case context survives symptom truncation and reaches the actual Critic request."""
import asyncio
import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "critic"))
from schemas import CaseContext, CriticReview, ReviewRequest
from critic import call_critic_agent
from agent_tools import Tools, VerifyArgs
from pipeline import Proposal

case = dict(crop="rice", region="Seoul", observed_date=date(2026, 7, 18),
            growth_stage="vegetative", affected_part="leaf", symptoms="x" * 5000)
context = CaseContext.from_case(case)
assert context.observed_date == date(2026, 7, 18)
assert CaseContext.from_case({}).model_dump() == dict(region="", observed_date=None, growth_stage="", affected_part="")
assert ReviewRequest(crop="rice", observations="Legacy input", candidates=[], evidence=[]).case_context == CaseContext()

class Reviewer:
    async def ainvoke(self, messages):
        payload = json.loads(messages[1].content)
        assert payload["case_context"] == dict(region="Seoul", observed_date="2026-07-18", growth_stage="vegetative", affected_part="leaf")
        assert "structured case_context" in messages[0].content
        return CriticReview(issues=[], limitations=[], review_summary="Fixture review")

async def main():
    await call_critic_agent(Reviewer(), ReviewRequest(case_context=context, crop="rice", observations=case["symptoms"], candidates=[], evidence=[]))
    evidence = dict(id="rice_001_f1", disease_id="rice_001", name_en="Rice blast", description="Fixture source", source_name="Fixture", source_location="Test")
    proposal = Proposal(candidates=[dict(id="rice_001", name="Rice blast", claim="Tentative", evidence_ids=[evidence["id"]])], summary="Fixture", limitations=[])
    state = dict(supporting_evidence=[evidence], judge_decisions=[], hypothesis_history=[], observed_symptoms=[case["symptoms"]], investigation_id="00000000-0000-0000-0000-000000000001", max_iterations=3)
    with patch("pipeline.generate", AsyncMock(return_value=proposal)), patch("agent_tools.create_critic_reviewer", return_value=Reviewer()), patch("agent_tools.database.save_round", AsyncMock()):
        result = await Tools(case, state).verify_evidence(VerifyArgs())
    assert result["action"] == "finalize"
    assert state["verified_fingerprint"]
    print("PASS actual verification tool retains structured case context with maximum-length symptoms")

asyncio.run(main())
print("PASS known/unknown context, dates, legacy API compatibility and serialized Critic input (mocked model)")
