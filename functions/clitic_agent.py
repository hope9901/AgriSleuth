# critic.py
import asyncio
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage


class CriticAgentError(RuntimeError):
    """Raised when the Critic Agent call fails."""


def load_prompt(prompt_path: str | Path) -> str:
    """Load a UTF-8 Markdown prompt."""
    path = Path(prompt_path).expanduser()

    # Resolve relative paths from this Python file's directory.
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path

    prompt = path.read_text(encoding="utf-8").strip()

    if not prompt:
        raise ValueError(f"Prompt file is empty: {path}")

    return prompt


async def call_critic_agent(
    reviewer: Any,
    review_input: dict,
    prompt_path: str | Path,
    timeout_seconds: float = 45,
) -> Any:
    """Call a model configured with a structured output schema."""
    import json

    # Configuration errors are raised before calling the model.
    system_prompt = load_prompt(prompt_path)
    input_json = json.dumps(
        review_input,
        ensure_ascii=False,
        allow_nan=False,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=input_json),
    ]

    try:
        async with asyncio.timeout(timeout_seconds):
            return await reviewer.ainvoke(messages)

    except TimeoutError:
        raise CriticAgentError("Critic Agent timed out.") from None

    except Exception:
        # Avoid exposing provider credentials or request contents.
        raise CriticAgentError("Critic Agent call failed.") from None
