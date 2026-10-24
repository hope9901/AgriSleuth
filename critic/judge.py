from schemas import CriticReview, JudgeAction


def judge_review(
    review: CriticReview,
    review_round: int,
) -> tuple[JudgeAction, str]:
    blockers = [
        issue
        for issue in review.issues
        if issue.severity == "blocking"
    ]

    if not blockers:
        if review.issues or review.limitations:
            return (
                "finalize_with_limitations",
                "No blocking issues; retain the reported limitations.",
            )

        return (
            "finalize",
            "No issues were identified by the Critic.",
        )

    # A round limit prevents further automated review.
    if review_round >= 3:
        return (
            "abstain",
            "Blocking issues remain after the review limit.",
        )

    actions = {issue.suggested_action for issue in blockers}

    # Address missing user observations before further automated work.
    if "request_user_input" in actions:
        return (
            "request_user_input",
            "Additional observations are required.",
        )

    if "retrieve_evidence" in actions:
        return (
            "retrieve_evidence",
            "Additional source evidence is required.",
        )

    return (
        "revise_conclusion",
        "The current conclusion must be revised.",
    )
