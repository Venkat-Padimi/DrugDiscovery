import logging
from typing import Optional, Dict, Any, Literal
from langgraph.graph import StateGraph, END

from src.domain.enums import WorkflowStage
from src.domain.state import ResearchGraphState
from src.agents.supervisor import SupervisorAgent
from src.agents.literature import LiteratureSearchAgent
from src.agents.target_id import TargetIdentificationAgent
from src.agents.evidence_eval import EvidenceEvaluationAgent
from src.agents.druggability import DruggabilityAgent
from src.agents.ranking import TargetRankingAgent
from src.agents.compound import CompoundScreeningAgent

logger = logging.getLogger(__name__)


def build_research_graph(
    supervisor_agent: Optional[SupervisorAgent] = None,
    literature_agent: Optional[LiteratureSearchAgent] = None,
    target_agent: Optional[TargetIdentificationAgent] = None,
    evidence_agent: Optional[EvidenceEvaluationAgent] = None,
    druggability_agent: Optional[DruggabilityAgent] = None,
    ranking_agent: Optional[TargetRankingAgent] = None,
    compound_agent: Optional[CompoundScreeningAgent] = None,
):
    """
    Constructs and compiles the stateful multi-agent LangGraph research workflow.
    
    WORKFLOW TOPOLOGY:
    Supervisor Plan
          ↓
    Literature Search
          ↓ (conditional: papers > 0 vs 0)
    [Target ID / Direct OpenTargets Fallback]
          ↓ (conditional: targets > 0 vs 0)
    Evidence Evaluation Agent
          ↓
    Druggability Assessment Agent
          ↓
    Target Ranking Agent (Deterministic Scoring Engine)
          ↓
    [Supervisor Synthesis / Insufficient Evidence Handler]
          ↓
         END
    """
    supervisor = supervisor_agent or SupervisorAgent()
    literature = literature_agent or LiteratureSearchAgent()
    target_id = target_agent or TargetIdentificationAgent()
    evidence_eval = evidence_agent or EvidenceEvaluationAgent()
    druggability = druggability_agent or DruggabilityAgent()
    ranking = ranking_agent or TargetRankingAgent()
    compound = compound_agent or CompoundScreeningAgent()

    # --- Node Definitions ---

    def node_supervisor_plan(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        return supervisor.plan(state)

    def node_literature_search(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        if state["step_count"] > state.get("max_steps", 15):
            supervisor.record_error(
                state=state,
                error_type="MaxStepsExceeded",
                message=f"Step count {state['step_count']} exceeded limit {state.get('max_steps', 15)}.",
                is_fatal=True,
            )
            return state
        return literature.run(state)

    def node_target_id(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        return target_id.run(state)

    def node_direct_target_id(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        supervisor.record_trace(
            state=state,
            input_summary="Literature returned 0 papers.",
            output_summary="Executing direct Open Targets query fallback.",
            tool_calls=["direct_open_targets_fallback()"],
            status="degraded",
            notes="No literature articles found. Relying on Open Targets direct association query.",
        )
        return target_id.run(state)

    def node_evidence_evaluation(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        return evidence_eval.run(state)

    def node_druggability_assessment(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        return druggability.run(state)

    def node_target_ranking(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        return ranking.run(state)

    def node_compound_screening(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        return compound.run(state)

    def node_insufficient_evidence(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        supervisor.record_error(
            state=state,
            error_type="InsufficientEvidence",
            message="No candidate targets could be identified from literature or Open Targets.",
            degradation_applied=True,
        )
        return supervisor.synthesize(state)

    def node_supervisor_synthesis(state: ResearchGraphState) -> ResearchGraphState:
        state["step_count"] = state.get("step_count", 0) + 1
        return supervisor.synthesize(state)

    # --- Conditional Edge Functions ---

    def route_after_literature(state: ResearchGraphState) -> Literal["node_target_id", "node_direct_target_id", "__end__"]:
        if state.get("step_count", 0) >= state.get("max_steps", 15):
            return END
        papers = state.get("retrieved_papers", [])
        if len(papers) > 0:
            return "node_target_id"
        return "node_direct_target_id"

    def route_after_target_id(state: ResearchGraphState) -> Literal["node_evidence_evaluation", "node_insufficient_evidence", "__end__"]:
        if state.get("step_count", 0) >= state.get("max_steps", 15):
            return END
        targets = state.get("identified_targets", {})
        if len(targets) == 0:
            return "node_insufficient_evidence"
        return "node_evidence_evaluation"

    def route_after_ranking(state: ResearchGraphState) -> Literal["node_compound_screening", "node_supervisor_synthesis", "__end__"]:
        if state.get("step_count", 0) >= state.get("max_steps", 15):
            return END
        if state.get("enable_compound_screening", True) and state.get("target_rankings"):
            return "node_compound_screening"
        return "node_supervisor_synthesis"

    # --- Build Graph ---
    graph = StateGraph(ResearchGraphState)

    graph.add_node("node_supervisor_plan", node_supervisor_plan)
    graph.add_node("node_literature_search", node_literature_search)
    graph.add_node("node_target_id", node_target_id)
    graph.add_node("node_direct_target_id", node_direct_target_id)
    graph.add_node("node_evidence_evaluation", node_evidence_evaluation)
    graph.add_node("node_druggability_assessment", node_druggability_assessment)
    graph.add_node("node_target_ranking", node_target_ranking)
    graph.add_node("node_compound_screening", node_compound_screening)
    graph.add_node("node_insufficient_evidence", node_insufficient_evidence)
    graph.add_node("node_supervisor_synthesis", node_supervisor_synthesis)

    graph.set_entry_point("node_supervisor_plan")
    graph.add_edge("node_supervisor_plan", "node_literature_search")

    graph.add_conditional_edges(
        "node_literature_search",
        route_after_literature,
        {
            "node_target_id": "node_target_id",
            "node_direct_target_id": "node_direct_target_id",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "node_target_id",
        route_after_target_id,
        {
            "node_evidence_evaluation": "node_evidence_evaluation",
            "node_insufficient_evidence": "node_insufficient_evidence",
            END: END,
        },
    )

    graph.add_conditional_edges(
        "node_direct_target_id",
        route_after_target_id,
        {
            "node_evidence_evaluation": "node_evidence_evaluation",
            "node_insufficient_evidence": "node_insufficient_evidence",
            END: END,
        },
    )

    graph.add_edge("node_evidence_evaluation", "node_druggability_assessment")
    graph.add_edge("node_druggability_assessment", "node_target_ranking")
    graph.add_conditional_edges(
        "node_target_ranking",
        route_after_ranking,
        {
            "node_compound_screening": "node_compound_screening",
            "node_supervisor_synthesis": "node_supervisor_synthesis",
            END: END,
        },
    )
    graph.add_edge("node_compound_screening", "node_supervisor_synthesis")
    graph.add_edge("node_insufficient_evidence", END)
    graph.add_edge("node_supervisor_synthesis", END)

    return graph.compile()


class ResearchWorkflowRunner:
    """
    Executable wrapper around the compiled multi-agent LangGraph workflow.
    """

    def __init__(
        self,
        supervisor_agent: Optional[SupervisorAgent] = None,
        literature_agent: Optional[LiteratureSearchAgent] = None,
        target_agent: Optional[TargetIdentificationAgent] = None,
        evidence_agent: Optional[EvidenceEvaluationAgent] = None,
        druggability_agent: Optional[DruggabilityAgent] = None,
        ranking_agent: Optional[TargetRankingAgent] = None,
        compound_agent: Optional[CompoundScreeningAgent] = None,
    ):
        self.app = build_research_graph(
            supervisor_agent=supervisor_agent,
            literature_agent=literature_agent,
            target_agent=target_agent,
            evidence_agent=evidence_agent,
            druggability_agent=druggability_agent,
            ranking_agent=ranking_agent,
            compound_agent=compound_agent,
        )

    def run(self, initial_state: ResearchGraphState) -> ResearchGraphState:
        """Executes the full research workflow from the initial state."""
        return self.app.invoke(initial_state)
