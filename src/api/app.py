import uuid
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field

from src.domain.state import create_initial_state, ResearchGraphState
from src.engine.workflow import ResearchWorkflowRunner
from src.engine.reporter import generate_research_report, report_to_markdown, report_to_json

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Drug Discovery & Target Identification Agent API",
    description="Agentic AI research platform API for biomedical literature search, target identification, multi-modal evidence evaluation, and deterministic ranking.",
    version="0.1.0",
)


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


@app.post("/api/investigate")
def run_investigation(request: InvestigationRequest) -> Dict[str, Any]:
    """
    Executes a full multi-agent research investigation synchronously and returns state.
    """
    session_id = f"API-{uuid.uuid4().hex[:8].upper()}"
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
        return final_state

    except Exception as exc:
        logger.error("Workflow execution failed in session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail=f"Workflow execution failure: {str(exc)}")


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
