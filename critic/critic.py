import asyncio
import os
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from schemas import CriticReview, ReviewRequest


PROMPT_PATH = (
    Path(__file__).resolve().parent / "prompts" / "clitic.md"
)


class CriticAgentError(RuntimeError):
    pass


def load_prompt(path: Path = PROMPT_PATH) -> str:
    prompt = path.read_text(encoding="utf-8").strip()

    if not prompt:
        raise ValueError("Critic prompt is empty.")

    return prompt


def create_critic_reviewer(
    base_url: str,
    model_name: str,
    api_key: str,
):
    from local_model import LocalStructuredModel
    return LocalStructuredModel(base_url,model_name,api_key,CriticReview,max_tokens=500)


async def call_critic_agent(
    reviewer,
    request: ReviewRequest,
) -> CriticReview:
    # Read on every call so prompt edits take effect immediately.
    system_prompt = load_prompt()

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=request.model_dump_json()),
    ]

    if hasattr(reviewer,'constrain_references'):
        reviewer.constrain_references([c.id for c in request.candidates],[e.id for e in request.evidence])

    try:
        async with asyncio.timeout(int(os.getenv('LOCAL_MODEL_TIMEOUT_SECONDS','180'))+5):
            result = await reviewer.ainvoke(messages)

        review = CriticReview.model_validate(result)

        candidate_ids = {item.id for item in request.candidates}
        evidence_ids = {item.id for item in request.evidence}

        # Validate references independently of the language model.
        for issue in review.issues:
            if (
                issue.candidate_id is not None
                and issue.candidate_id not in candidate_ids
            ):
                raise ValueError("Unknown candidate ID.")

            if set(issue.evidence_ids) - evidence_ids:
                raise ValueError("Unknown evidence ID.")

        evidence_by_id={item.id:item for item in request.evidence}
        for issue in review.issues:
            if issue.code=='OBSERVATION_MISMATCH' and issue.candidate_id and issue.evidence_ids:
                attributed=[evidence_by_id[i].disease_id for i in issue.evidence_ids]
                if all(attributed) and issue.candidate_id not in attributed:
                    raise ValueError("Mismatch references only another disease's evidence.")

        return review

    except TimeoutError:
        raise CriticAgentError("Critic Agent timed out.") from None

    except Exception:
        raise CriticAgentError(
            "Critic call or response validation failed."
        ) from None
