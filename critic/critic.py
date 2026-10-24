import asyncio
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from schemas import CriticReview, ReviewRequest


PROMPT_PATH = (
    Path(__file__).resolve().parent / "prompts" / "critic.md"
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
    model = ChatOpenAI(
        base_url=base_url,
        model=model_name,
        api_key=api_key,
        temperature=0.1,
        max_tokens=1200,
        timeout=90,
        max_retries=0,
    )

    return model.with_structured_output(
        CriticReview,
        method="json_schema",
    )


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

    try:
        async with asyncio.timeout(95):
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

        return review

    except TimeoutError:
        raise CriticAgentError("Critic Agent timed out.") from None

    except Exception:
        raise CriticAgentError(
            "Critic call or response validation failed."
        ) from None
