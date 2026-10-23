from datetime import date
from typing import Literal, TypedDict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


# ---------- API 입력·출력 ----------

class InvestigationRequest(BaseModel):
    crop: Literal["rice", "maize"]
    region: str = Field(default="", max_length=200)
    observed_date: date | None = None
    symptoms: str = Field(default="", max_length=5000)


class InvestigationResponse(BaseModel):
    status: Literal["needs_input", "ready"]
    summary: str
    questions: list[str]
    trace: list[str]


# ---------- 노드들이 공유하는 상태 ----------

class InvestigationState(TypedDict):
    crop: str
    region: str
    observed_date: str
    symptoms: str
    missing_fields: list[str]
    questions: list[str]
    status: str
    summary: str
    trace: list[str]


# ---------- 노드 ----------

def validate_input(state: InvestigationState) -> dict:
   quired_fields = {
        "region": "재배 지역을 알려주세요.",
        "observed_date": "증상을 관찰한 날짜를 알려주세요.",
        "symptoms": "어느 부위에 어떤 증상이 나타났는지 알려주세요.",
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


def route_after_validation(
    state: InvestigationState,
) -> Literal["request_input", "prepare_investigation"]:
    """입력 상태에 따라 다음 노드를 선택한다."""
    if state["missing_fields"]:
        return "request_input"

    return "prepare_investigation"


def request_input(state: InvestigationState) -> dict:
    """사용자가 추가 정보를 입력하도록 안내한다."""
    return {
        "status": "needs_input",
        "summary": "조사를 시작í¥¼ 연결할 위치."""
    crop_name = {"rice": "벼", "maize": "옥수수"}[state["crop"]]

    return {
        "status": "ready",
        "summary": (
            f"{state['region']}에서 {state['observed_date']}에 관찰한 "
            f"{crop_name} 증상 정보를 접수했습니다. "
            "병해 자료 검색과 AI 분석은 아직 연결되지 않았습니다."
        ),
        "questions": [],
        "trace": state["trace"] + ["prepare_investigation"],
    }


# ---------- 그래프 구성 ----------

builder = StateGraph(InvestigationState)

builder.add_node("validate_input", validate_input)
builder.add_node("request_input", request_input)
builder.add_node("prepare_investigation", prepare_investigation)

builder.add_edge(START, "validate_input")

builder.add_conditional_edges(
    "validate_input",
    route_after_validation,
    {
        "request_input": "request_input",
        "prepare_investigation": "prepare_investigation",
    },
)

builder.add_edge("request_input", END)
bAPI ----------

app = FastAPI(title="AgriSleuth API", version="0.1.0")

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
    return {"status": "ok"}


@app.post("/investigations", response_model=InvestigationResponse)
async def investigate(
    request: InvestigationRequest,
) -> InvestigationResponse:
    initial_state: InvestigationState = {
        "crop": request.crop,
        "region": request.region.strip(),
        "observed_date": (
            request.observed_date.isoformat()
            if request.observed_date
            else ""
        ),
        "symptoms": request.symptoms.strip(),
        "missing_fields": [],
        "questions": [],
        "status": "",
        "summary": "",
        "trace": [],
    }

    result = await investigation_graph.ainvoke(initial_state)

    return InvestigationResponse(
        status=result["status"],
        summary=result["summary"],
        questions=result["questions"],
        trace=result["trace"],
    )
