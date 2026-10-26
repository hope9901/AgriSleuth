from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InvestigationRequest(Schema):
    crop: Literal["rice", "maize"]
    region: str = Field(default="", max_length=200)
    observed_date: date | None = None
    symptoms: str = Field(default="", max_length=5000)


class InvestigationEvent(Schema):
    id: str
    timestamp: str
    node: str
    summary: str


class InvestigationResponse(Schema):
    id: str
    photoId: str | None = None
    status: Literal["needs_input", "ready", "researching", "reviewing", "completed", "needs_more_evidence", "abstained", "failed"]
    summary: str
    questions: list[str]
    hypotheses: list[dict] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    reviewIssues: list[dict] = Field(default_factory=list)
    nextAction: str | None = None
    limitations: list[str] = Field(default_factory=list)
    events: list[InvestigationEvent] = Field(default_factory=list)


class Evidence(Schema):
    disease_id: str | None = None
    disease_name: str | None = None
    id: str
    text: str = Field(min_length=1, max_length=4000)
    source: str
    location: str


class Candidate(Schema):
    id: str
    name: str
    claim: str
    evidence_ids: list[str]


class ReviewRequest(Schema):
    crop: Literal["rice", "maize"]
    observations: str = Field(min_length=1, max_length=5000)
    candidates: list[Candidate] = Field(max_length=3)
    evidence: list[Evidence] = Field(max_length=8)
    weather_summary: str = Field(
        default="Weather evidence is unavailable.",
        max_length=2000,
    )
    review_round: int = Field(default=1, ge=1, le=3)

    @model_validator(mode="after")
    def validate_references(self):
        evidence_ids = [item.id for item in self.evidence]
        candidate_ids = [item.id for item in self.candidates]

        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Evidence IDs must be unique.")

        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Candidate IDs must be unique.")

        known = set(evidence_ids)

        for candidate in self.candidates:
            if set(candidate.evidence_ids) - known:
                raise ValueError("Candidate references unknown evidence.")

        return self


class CriticIssue(Schema):
    code: Literal[
        "UNSUPPORTED_CLAIM",
        "OBSERVATION_MISMATCH",
        "MISSING_DIFFERENTIAL",
        "WEATHER_CONTEXT_GAP",
        "OVERCONFIDENT_CONCLUSION",
    ]
    severity: Literal["blocking", "advisory"]
    candidate_id: str | None
    reason: str
    evidence_ids: list[str]
    suggested_action: Literal[
        "retrieve_evidence",
        "request_user_input",
        "revise_conclusion",
    ]
    requested_information: str


class CriticReview(Schema):
    issues: list[CriticIssue]
    limitations: list[str]
    review_summary: str


JudgeAction = Literal[
    "finalize",
    "finalize_with_limitations",
    "request_user_input",
    "retrieve_evidence",
    "revise_conclusion",
    "abstain",
]


class ReviewResponse(Schema):
    review: CriticReview | None
    action: JudgeAction
    reason: str
    review_round: int
    trace: list[str]
