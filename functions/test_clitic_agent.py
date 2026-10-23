from critic import call_critic_agent
from schemas import CriticReview

# Create this once during application startup.
reviewer = model.with_structured_output(CriticReview)


async def critic_node(state):
    review = await call_critic_agent(
        reviewer=reviewer,
        review_input=state["review_input"],
        prompt_path="prompts/critic.md",
    )

    return {
        "critic_review": review.model_dump(),
        "review_round": state.get("review_round", 0) + 1,
    }
