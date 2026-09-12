from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.domain.enums import WorkflowStage
from src.domain.models import (
    PubMedArticle,
    TargetCandidate,
    EvidenceItem,
    DruggabilityProfile,
    ExperimentalRecord,
    RankedTarget,
    CompoundBioactivity,
    ScreeningPrediction,
    AgentTraceEvent,
    ResearchReport,
)


class WorkflowError(BaseModel):
    """Structured error event encountered during agent execution."""
    stage: WorkflowStage
    agent_name: str
    error_type: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_fatal: bool = False
    degradation_applied: bool = False


class ResearchGraphState(TypedDict, total=False):
    """
    Strongly typed state dictionary passed through the LangGraph multi-agent workflow.
    Every agent reads from and mutates specific partitions of this state.
    """
    # Investigation metadata
    session_id: str
    research_question: str
    disease_name: str
    disease_efo_id: Optional[str]
    created_at: str
    current_stage: str
    status: str  # "initializing", "in_progress", "completed", "degraded", "failed"

    # Pipeline parameters
    scoring_weights: Dict[str, float]
    enable_compound_screening: bool
    max_literature_results: int
    top_n_targets_to_screen: int

    # Literature search phase
    literature_search_queries: List[str]
    retrieved_papers: List[Dict[str, Any]]  # Serialized PubMedArticle
    paper_dois_or_pmids: List[str]

    # Target identification phase
    identified_targets: Dict[str, Dict[str, Any]]  # symbol -> TargetCandidate dict

    # Evidence evaluation phase
    evidence_records: List[Dict[str, Any]]  # List of EvidenceItem dicts

    # Tractability / druggability phase
    druggability_assessments: Dict[str, Dict[str, Any]]  # symbol -> DruggabilityProfile dict

    # Experimental data integration phase
    experimental_data_matches: Dict[str, List[Dict[str, Any]]]  # symbol -> List[ExperimentalRecord] dicts

    # Target ranking phase
    target_rankings: List[Dict[str, Any]]  # List of RankedTarget dicts

    # Compound screening phase (optional / conditional)
    known_active_compounds: Dict[str, List[Dict[str, Any]]]  # symbol -> List[CompoundBioactivity] dicts
    compound_screenings: Dict[str, List[Dict[str, Any]]]  # symbol -> List[ScreeningPrediction] dicts

    # Observability & reporting
    step_count: int
    max_steps: int
    executive_summary: Optional[str]
    audit_trace: List[Dict[str, Any]]  # List of AgentTraceEvent dicts
    errors: List[Dict[str, Any]]  # List of WorkflowError dicts
    final_report: Optional[Dict[str, Any]]  # Serialized ResearchReport


def create_initial_state(
    session_id: str,
    research_question: str,
    disease_name: str,
    disease_efo_id: Optional[str] = None,
    scoring_weights: Optional[Dict[str, float]] = None,
    enable_compound_screening: bool = True,
    max_literature_results: int = 15,
    max_steps: int = 15,
) -> ResearchGraphState:
    """Helper to initialize a clean ResearchGraphState for a new investigation."""
    default_weights = {
        "disease_association": 0.25,
        "genetic_evidence": 0.20,
        "target_tractability": 0.20,
        "literature_evidence": 0.15,
        "experimental_validation": 0.10,
        "safety_profile": 0.10,
    }
    return {
        "session_id": session_id,
        "research_question": research_question,
        "disease_name": disease_name,
        "disease_efo_id": disease_efo_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "current_stage": WorkflowStage.INITIALIZATION.value,
        "status": "initializing",
        "scoring_weights": scoring_weights or default_weights,
        "enable_compound_screening": enable_compound_screening,
        "max_literature_results": max_literature_results,
        "top_n_targets_to_screen": 5,
        "step_count": 0,
        "max_steps": max_steps,
        "executive_summary": None,
        "literature_search_queries": [],
        "retrieved_papers": [],
        "paper_dois_or_pmids": [],
        "identified_targets": {},
        "evidence_records": [],
        "druggability_assessments": {},
        "experimental_data_matches": {},
        "target_rankings": [],
        "known_active_compounds": {},
        "compound_screenings": {},
        "audit_trace": [],
        "errors": [],
        "final_report": None,
    }
