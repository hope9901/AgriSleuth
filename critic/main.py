import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from io import BytesIO
from uuid import UUID, uuid4
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Response
import psycopg
from database import save_investigation, get_investigation, get_photo
from PIL import Image, UnidentifiedImageError
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
    events: list[dict]


def execution_event(node: str, summary: str) -> dict:
    return {
        "id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": node,
        "summary": summary,
    }


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
        "events": state["events"] + [execution_event("validate_input", "Checked required observation fields.")],
    }


def route_intake(state: IntakeState) -> str:
    return "request_input" if state["missing_fields"] else "prepare"


def request_input(state: IntakeState) -> dict:
    return {
        "status": "needs_input",
        "summary": "Additional observation information is required.",
        "trace": state["trace"] + ["request_input"],
        "events": state["events"] + [execution_event("request_input", "Returned questions for missing fields.")],
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
        "events": state["events"] + [execution_event("prepare", "Input validation completed; analysis is not connected.")],
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

    model_name = os.getenv("LM_STUDIO_MODEL", "").strip()
    app.state.review_graph = None
    if model_name:
        reviewer = create_critic_reviewer(
            base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
            model_name=model_name,
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


@app.post("/api/investigations", response_model=InvestigationResponse)
async def investigate(
    crop: str = Form(..., pattern="^(rice|maize)$"),
    region: str = Form("", max_length=200),
    observed_date: str = Form("", max_length=10),
    symptoms: str = Form("", max_length=5000),
    growth_stage: str = Form("", max_length=100),
    affected_part: str = Form("", max_length=100),
    photo: UploadFile = File(...),
):
    if observed_date:
        try:
            observed_date = date.fromisoformat(observed_date).isoformat()
        except ValueError:
            raise HTTPException(422, "Observation date must be YYYY-MM-DD.") from None

    allowed = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
    try:
        if photo.content_type not in allowed:
            raise HTTPException(415, "Use a JPG, PNG or WEBP photograph.")
        contents = await photo.read(10 * 1024 * 1024 + 1)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(413, "Photograph must not exceed 10 MB.")
        try:
            with Image.open(BytesIO(contents)) as image:
                if image.format != allowed[photo.content_type]:
                    raise HTTPException(415, "Image contents do not match the declared type.")
                width, height = image.size
                image.verify()
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
            raise HTTPException(422, "The photograph is invalid or unsupported.") from None
    finally:
        await photo.close()

    result = await intake_graph.ainvoke({
        "region": region.strip(),
        "observed_date": observed_date,
        "symptoms": symptoms.strip(),
        "missing_fields": [], "questions": [], "status": "", "summary": "",
        "trace": [],
        "events": [execution_event("validate_upload", "Validated image type, contents and size.")],
    })
    photo_id = str(uuid4())
    response = InvestigationResponse(
        id=str(uuid4()),
        photoId=photo_id,
        status=result["status"],
        summary=result["summary"],
        questions=result["questions"],
        nextAction=("Provide the missing observations." if result["status"] == "needs_input"
                    else "Evidence retrieval and candidate generation must be connected before review."),
        limitations=[
            "This endpoint validates inputs only; no image analysis or disease review has run.",
            "Growth stage and affected part are stored but not used for analysis yet.",
        ],
        events=result["events"],
    )
    try:
        await save_investigation(
            result=response, crop=crop, region=region.strip(),
            observed_date=date.fromisoformat(observed_date) if observed_date else None,
            growth_stage=growth_stage, affected_part=affected_part, symptoms=symptoms.strip(),
            photo_id=photo_id, filename=photo.filename,
            content_type=photo.content_type, width=width, height=height, contents=contents,
        )
    except (psycopg.Error, RuntimeError):
        raise HTTPException(503, "Investigation storage is unavailable. Nothing was saved.") from None
    return response


@app.get("/api/investigations/{investigation_id}", response_model=InvestigationResponse)
async def read_investigation(investigation_id: UUID):
    try:
        result = await get_investigation(investigation_id)
    except (psycopg.Error, RuntimeError):
        raise HTTPException(503, "Investigation storage is unavailable.") from None
    if result is None:
        raise HTTPException(404, "Investigation not found.")
    return result


@app.get("/api/photos/{photo_id}")
async def read_photo(photo_id: UUID):
    try:
        photo = await get_photo(photo_id)
    except (psycopg.Error, RuntimeError):
        raise HTTPException(503, "Photo storage is unavailable.") from None
    if photo is None:
        raise HTTPException(404, "Photo not found.")
    return Response(content=bytes(photo["content"]), media_type=photo["content_type"],
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.post("/api/reviews", response_model=ReviewResponse)
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

    if app.state.review_graph is None:
        raise HTTPException(503, "Configure LM_STUDIO_MODEL to enable Critic review.")

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


# Weather retrieval runs separately so observation uploads remain responsive.
from fastapi import Query
from pydantic import BaseModel, Field
import asyncio
from weather import WeatherError, search_locations, fetch_weather, compare_conditions
from database import weather_case, save_weather, read_weather

class WeatherRequest(BaseModel):
    location_id: int = Field(gt=0)

@app.get('/api/weather/locations')
async def weather_locations(q: str = Query(min_length=2,max_length=200)):
    try:
        return {'locations': await search_locations(q.strip()),
                'attribution': 'Location data: GeoNames via Open-Meteo. Weather observations: KMA.'}
    except WeatherError as exc:
        raise HTTPException(502,str(exc)) from None

@app.get('/api/investigations/{investigation_id}/weather')
async def get_case_weather(investigation_id: UUID):
    try:
        report = await read_weather(investigation_id)
    except (psycopg.Error,RuntimeError):
        raise HTTPException(503,'Weather storage is unavailable.') from None
    if report is None: raise HTTPException(404,'No saved weather evidence for this investigation.')
    return report

@app.post('/api/investigations/{investigation_id}/weather')
async def collect_case_weather(investigation_id: UUID, request: WeatherRequest):
    try:
        case, diseases = await weather_case(investigation_id)
        if case is None: raise HTTPException(404,'Investigation not found.')
        if case['observed_date'] is None: raise HTTPException(422,'An observation date is required.')
        try:
            report = await asyncio.wait_for(fetch_weather(request.location_id,case['observed_date']),timeout=45)
        except (WeatherError,asyncio.TimeoutError) as exc:
            report = dict(status='unavailable',observations=[],summary={},comparisons=[],
                observed_date=case['observed_date'].isoformat(),
                limitations=[str(exc) if isinstance(exc,WeatherError) else 'Weather request timed out.'])
        report['region_entered'] = case['region']
        report['comparisons'] = compare_conditions(diseases,report) if report['observations'] else []
        await save_weather(investigation_id,request.location_id,report)
        return report
    except (psycopg.Error,RuntimeError):
        raise HTTPException(503,'Weather storage is unavailable; evidence was not saved.') from None
