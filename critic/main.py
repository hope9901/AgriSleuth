import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import END, START, StateGraph

from critic import (
    CriticAgentError,
    call_critic_agent,
    create_critic_reviewer,
    load_prompt,
)
from judge import judge_review
from schemas import (
    CriticReview,
    InvestigationRequest,
    InvestigationResponse,
    ReviewRequest,
    ReviewResponse,
)


load_dotenv(Path(__file__).resolve().parent / ".env")


# ---------- Original intake workflow ----------

class IntakeState(TypedDict):
    region: str
    observed_date: str
    symptoms: str
    missing_fields: list[str]
    questions: list[str]
    status: str
    summary: str
    trace: list[str]


def validate_input(state: IntakeState) -> dict:
    required_fields = {
        "region": "Please provide the growing location.",
        "observed_date": "Please provide the observation date.",
        "symptoms": "Please describe the observed symptoms.",
    }

    missing = [
        field
        for field in required_fields
        if not state[field].strip()
    ]

    return {
        "missing_fields": missing,
        "questions": [required_fields[field] for field in missing],
        "trace": state["trace"] + ["validate_input"],
    }


def route_intake(state: IntakeState) -> str:
    return "request_input" if state["missing_fields"] else "prepare"


def request_input(state: IntakeState) -> dict:
    return {
        "status": "needs_input",
        "summary": "Additional observation information is required.",
        "trace": state["trace"] + ["request_input"],
    }


def prepare(state: IntakeState) -> dict:
    return {
        "status": "ready",
        "summary": (
            "Observations validated. Disease retrieval and candidate "
            "generation are not connected yet."
        ),
        "questions": [],
        "trace": state["trace"] + ["prepare"],
    }


intake_builder = StateGraph(IntakeState)
intake_builder.add_node("validate_input", validate_input)
intake_builder.add_node("request_input", request_input)
intake_builder.add_node("prepare", prepare)
intake_builder.add_edge(START, "validate_input")
intake_builder.add_conditional_edges(
    "validate_input",
    route_intake,
    {"request_input": "request_input", "prepare": "prepare"},
)
intake_builder.add_edge("request_input", END)
intake_builder.add_edge("prepare", END)
intake_graph = intake_builder.compile()


# ---------- Critic / Judge workflow ----------

class ReviewState(TypedDict):
    request: ReviewRequest
    review: CriticReview | None
    action: str
    reason: str
    trace: list[str]


def build_review_graph(reviewer):
    async def critic_node(state: ReviewState) -> dict:
        review = await call_critic_agent(
            reviewer,
            state["request"],
        )
        return {
            "review": review,
            "trace": state["trace"] + ["critic"],
        }

    def judge_node(state: ReviewState) -> dict:
        review = state["review"]

        if review is None:
            raise RuntimeError("Critic review is missing.")

        action, reason = judge_review(
            review,
            state["request"].review_round,
        )

        return {
            "action": action,
            "reason": reason,
            "trace": state["trace"] + ["judge"],
        }

    builder = StateGraph(ReviewState)
    builder.add_node("critic", critic_node)
    builder.add_node("judge", judge_node)
    builder.add_edge(START, "critic")
    builder.add_edge("critic", "judge")
    builder.add_edge("judge", END)

    return builder.compile()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail early on a missing/empty prompt or missing configuration.
    load_prompt()

    reviewer = create_critic_reviewer(
        base_url=os.getenv(
            "LM_STUDIO_BASE_URL",
            "http://localhost:1234/v1",
        ),
        model_name=os.environ["LM_STUDIO_MODEL"],
        api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
    )

    app.state.review_graph = build_review_graph(reviewer)
    yield


app = FastAPI(
    title="AgriSleuth API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    # Process health only; this does not check the model server.
    return {"status": "ok"}


@app.post(
    "/investigations",
    response_model=InvestigationResponse,
)
async def investigate(request: InvestigationRequest):
    result = await intake_graph.ainvoke({
        "region": request.region.strip(),
        "observed_date": (
            request.observed_date.isoformat()
            if request.observed_date else ""
        ),
        "symptoms": request.symptoms.strip(),
        "missing_fields": [],
        "questions": [],
        "status": "",
        "summary": "",
        "trace": [],
    })

    return InvestigationResponse(
        status=result["status"],
        summary=result["summary"],
        questions=result["questions"],
        trace=result["trace"],
    )


@app.post("/reviews", response_model=ReviewResponse)
async def review_candidates(request: ReviewRequest):
    # No candidates/evidence: do not ask the model to invent them.
    if not request.candidates or not request.evidence:
        return ReviewResponse(
            review=None,
            action="retrieve_evidence",
            reason="Candidates and source evidence are required.",
            review_round=request.review_round,
            trace=[],
        )

    try:
        result = await app.state.review_graph.ainvoke({
            "request": request,
            "review": None,
            "action": "",
            "reason": "",
            "trace": [],
        })
    except CriticAgentError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from None

    return ReviewResponse(
        review=result["review"],
        action=result["action"],
        reason=result["reason"],
        review_round=request.review_round,
        trace=result["trace"],
    )
