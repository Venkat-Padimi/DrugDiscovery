import uuid
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from src.domain.state import create_initial_state, ResearchGraphState
from src.engine.workflow import ResearchWorkflowRunner
from src.engine.reporter import generate_research_report, report_to_markdown, report_to_json
from src.engine.graph_builder import build_discovery_graph
from src.ui.helpers import get_sample_presets, extract_target_detail

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Drug Discovery & Target Identification Agent API",
    description="Agentic AI research platform API for biomedical literature search, target identification, multi-modal evidence evaluation, and deterministic ranking.",
    version="0.1.0",
)

# Enable CORS for React frontend (Vite dev server and production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (keyed by session_id, also stores "latest")
SESSION_STORE: Dict[str, Dict[str, Any]] = {}


class InvestigationRequest(BaseModel):
    research_question: str = Field(..., description="Natural language biomedical research question")
    disease_name: Optional[str] = Field(None, description="Explicit disease name (optional, auto-extracted if omitted)")
    disease_efo_id: Optional[str] = Field(None, description="Optional ontology EFO ID")
    enable_compound_screening: bool = Field(True, description="Whether to run compound screening stage")
    top_n_targets_to_screen: int = Field(5, ge=1, le=20, description="Top N targets to screen")
    max_literature_results: int = Field(15, ge=1, le=50, description="Max PubMed papers to fetch")
    scoring_weights: Optional[Dict[str, float]] = Field(None, description="Custom 6-factor deterministic scoring weights")


class HealthResponse(BaseModel):
    status: str
    version: str
    platform: str
    workflow_stages: List[str]


def _resolve_session(session_id: str) -> Dict[str, Any]:
    """Helper to look up session from store, supporting 'latest'."""
    if session_id in SESSION_STORE:
        return SESSION_STORE[session_id]
    if session_id == "latest" and "latest" in SESSION_STORE:
        return SESSION_STORE["latest"]
    # Check case-insensitive
    for sid, st in SESSION_STORE.items():
        if sid.lower() == session_id.lower():
            return st
    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found in active session store")


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint exposing active platform capabilities."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        platform="Drug Discovery & Target Identification Research Platform",
        workflow_stages=[
            "supervisor_plan",
            "literature_search",
            "target_identification",
            "evidence_evaluation",
            "druggability_assessment",
            "target_ranking",
            "compound_screening",
            "supervisor_synthesis",
        ],
    )


@app.get("/api/presets")
def list_presets() -> Dict[str, Dict[str, Any]]:
    """Returns curated demonstration research query presets."""
    return get_sample_presets()


@app.post("/api/investigate")
def run_investigation(request: InvestigationRequest) -> Dict[str, Any]:
    """
    Executes a full multi-agent research investigation synchronously, saves state, and returns it.
    """
    session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"
    logger.info("Initiating research investigation session %s for question '%s'", session_id, request.research_question)

    try:
        initial_state = create_initial_state(
            session_id=session_id,
            research_question=request.research_question,
            disease_name=request.disease_name or "",
            disease_efo_id=request.disease_efo_id,
            scoring_weights=request.scoring_weights,
            enable_compound_screening=request.enable_compound_screening,
            max_literature_results=request.max_literature_results,
        )
        initial_state["top_n_targets_to_screen"] = request.top_n_targets_to_screen

        runner = ResearchWorkflowRunner()
        final_state = runner.run(initial_state)

        # Store in session cache
        SESSION_STORE[session_id] = final_state
        SESSION_STORE["latest"] = final_state

        return final_state

    except Exception as exc:
        logger.error("Workflow execution failed in session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Workflow execution failure: {str(exc)}")


@app.get("/api/sessions")
def list_sessions() -> List[Dict[str, Any]]:
    """Lists summary metadata of all executed investigations."""
    summaries = []
    seen = set()
    for sid, st in SESSION_STORE.items():
        if sid == "latest" or sid in seen:
            continue
        seen.add(sid)
        summaries.append({
            "session_id": sid,
            "disease_name": st.get("disease_name", ""),
            "research_question": st.get("research_question", ""),
            "status": st.get("status", "completed"),
            "target_count": len(st.get("target_rankings", [])),
            "created_at": st.get("created_at", ""),
        })
    return summaries


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    """Returns full workflow state for a given session."""
    return _resolve_session(session_id)


@app.get("/api/sessions/{session_id}/targets")
def get_session_targets(session_id: str) -> List[Dict[str, Any]]:
    """Returns ranked therapeutic candidate targets with scores and tiers."""
    state = _resolve_session(session_id)
    return state.get("target_rankings", [])


@app.get("/api/sessions/{session_id}/targets/{target_symbol}")
def get_session_target_detail(session_id: str, target_symbol: str) -> Dict[str, Any]:
    """Returns deep-dive multi-modal dossier for a specific target symbol."""
    state = _resolve_session(session_id)
    detail = extract_target_detail(state, target_symbol)
    if not detail or not detail.get("ranking"):
        raise HTTPException(status_code=404, detail=f"Target '{target_symbol}' not found in session '{session_id}'")
    return detail


@app.get("/api/sessions/{session_id}/compounds")
def get_session_compounds(session_id: str) -> Dict[str, Any]:
    """
    Returns empirical bioactivity compounds and computational screening predictions
    with mandatory in silico disclaimers.
    """
    state = _resolve_session(session_id)
    return {
        "known_active_compounds": state.get("known_active_compounds", {}),
        "compound_screenings": state.get("compound_screenings", {}),
        "disclaimer": "Computational simulation predictions are in silico models and not experimentally measured bioactivities.",
    }


@app.get("/api/sessions/{session_id}/evidence")
def get_session_evidence(session_id: str) -> List[Dict[str, Any]]:
    """Returns all evidence items linked across targets."""
    state = _resolve_session(session_id)
    return state.get("evidence_records", [])


@app.get("/api/sessions/{session_id}/audit")
def get_session_audit(session_id: str) -> List[Dict[str, Any]]:
    """Returns the agent audit trace records."""
    state = _resolve_session(session_id)
    return state.get("audit_trace", [])


@app.get("/api/sessions/{session_id}/graph")
def get_session_graph(session_id: str, max_targets: int = 6) -> Dict[str, Any]:
    """
    Constructs a deterministic React Flow graph structure (nodes, edges, metadata)
    from verified state entities.
    """
    state = _resolve_session(session_id)
    return build_discovery_graph(state, max_targets=max_targets)


@app.post("/api/report")
def generate_report(state: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generates a structured ResearchReport and rendered Markdown from workflow state.
    """
    try:
        report = generate_research_report(state)
        md = report_to_markdown(report, state=state)
        return {
            "report": report.model_dump(mode="json"),
            "markdown": md,
        }
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Failed to generate report from state: {str(exc)}")


@app.get("/api/sessions/{session_id}/report")
def get_session_report(session_id: str) -> Dict[str, Any]:
    """Generates and returns the research report for a stored session."""
    state = _resolve_session(session_id)
    report = generate_research_report(state)
    md = report_to_markdown(report, state=state)
    return {
        "report": report.model_dump(mode="json"),
        "markdown": md,
    }


# Mount built React frontend if dist directory exists
from pathlib import Path
from fastapi.staticfiles import StaticFiles

_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")

