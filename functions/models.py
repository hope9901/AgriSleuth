from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WeatherQuery(Schema):
    station_id: str = Field(pattern=r"^\d{2,4}$")
    start: date
    end: date

    @model_validator(mode="after")
    def check_period(self):
        if not 0 <= (self.end - self.start).days <= 30:
            raise ValueError("Request a period of 1 to 31 days.")
        return self


class WeatherDay(Schema):
    observed_date: date
    mean_temperature_c: float | None
    mean_humidity_pct: float | None
    precipitation_mm: float | None


class WeatherContext(Schema):
    status: Literal["available", "partial", "unavailable"]
    query: WeatherQuery
    retrieved_at: datetime
    days: list[WeatherDay] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source: str = "KMA ASOS daily observations"


class Evidence(Schema):
    id: str
    text: str
    url: str
    location: str


class Candidate(Schema):
    id: str
    explanation: str
    evidence_ids: list[str]


class ReviewInput(Schema):
    crop: Literal["rice", "maize"]
    user_observations: str
    image_observations: list[str] = Field(default_factory=list)
    candidates: list[Candidate]
    evidence: list[Evidence]
    weather: WeatherContext

    @model_validator(mode="after")
    def check_references(self):
        evidence_ids = [item.id for item in self.evidence]
        candidate_ids = [item.id for item in self.candidates]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("Duplicate evidence IDs.")
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("Duplicate candidate IDs.")
        known = set(evidence_ids)
        if any(set(c.evidence_ids) - known for c in self.candidates):
            raise ValueError("Candidate references unknown evidence.")
        return self


class ReviewIssue(Schema):
    code: Literal["UNSUPPORTED_CLAIM", "OBSERVATION_MISMATCH",
                  "MISSING_DIFFERENTIAL", "WEATHER_CONTEXT_GAP",
                  "OVERCONFIDENT_CONCLUSION"]
    severity: Literal["blocking", "advisory"]
    candidate_id: str | None
    reason: str
    evidence_ids: list[str]
    suggested_action: Literal["retrieve_evidence", "request_user_input",
                              "revise_conclusion"]
    requested_information: str


class CriticReview(Schema):
    issues: list[ReviewIssue]
    limitations: list[str]
    review_summary: str
