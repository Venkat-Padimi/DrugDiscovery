import pytest

from src.domain.enums import WorkflowStage
from src.domain.state import create_initial_state, WorkflowError, ResearchGraphState


class TestStateTransitions:

    def test_create_initial_state_defaults(self):
        state = create_initial_state(
            session_id="SESSION-001",
            research_question="Identify therapeutic targets for Alzheimer's disease.",
            disease_name="Alzheimer's disease",
            disease_efo_id="EFO_0000249",
        )

        assert state["session_id"] == "SESSION-001"
        assert state["disease_name"] == "Alzheimer's disease"
        assert state["current_stage"] == WorkflowStage.INITIALIZATION.value
        assert state["status"] == "initializing"
        assert len(state["identified_targets"]) == 0
        assert len(state["retrieved_papers"]) == 0
        assert len(state["evidence_records"]) == 0
        assert len(state["target_rankings"]) == 0
        assert state["scoring_weights"]["disease_association"] == 0.25

    def test_custom_scoring_weights(self):
        custom_weights = {
            "disease_association": 0.30,
            "genetic_evidence": 0.30,
            "target_tractability": 0.20,
            "literature_evidence": 0.10,
            "experimental_validation": 0.05,
            "safety_profile": 0.05,
        }
        state = create_initial_state(
            session_id="SESSION-002",
            research_question="Investigate ALS targets.",
            disease_name="Amyotrophic lateral sclerosis",
            scoring_weights=custom_weights,
        )
        assert state["scoring_weights"]["genetic_evidence"] == 0.30

    def test_simulated_stage_transitions(self):
        state = create_initial_state(
            session_id="SESSION-003",
            research_question="Query Parkinson's targets.",
            disease_name="Parkinson's disease",
        )

        # Transition to literature search
        state["current_stage"] = WorkflowStage.LITERATURE_SEARCH.value
        state["status"] = "in_progress"
        state["literature_search_queries"].append("Parkinson's disease AND therapeutic target")
        assert len(state["literature_search_queries"]) == 1

        # Transition to target identification
        state["current_stage"] = WorkflowStage.TARGET_IDENTIFICATION.value
        state["identified_targets"]["SNCA"] = {
            "target_symbol": "SNCA",
            "disease_name": "Parkinson's disease",
        }
        assert "SNCA" in state["identified_targets"]

        # Transition to target ranking
        state["current_stage"] = WorkflowStage.TARGET_RANKING.value
        state["target_rankings"].append({
            "target_symbol": "SNCA",
            "overall_priority_score": 88.5,
        })
        assert len(state["target_rankings"]) == 1

        # Completed
        state["current_stage"] = WorkflowStage.COMPLETED.value
        state["status"] = "completed"
        assert state["status"] == "completed"

    def test_workflow_error_logging(self):
        state = create_initial_state(
            session_id="SESSION-004",
            research_question="Query Huntington targets.",
            disease_name="Huntington's disease",
        )

        err = WorkflowError(
            stage=WorkflowStage.LITERATURE_SEARCH,
            agent_name="LiteratureSearchAgent",
            error_type="NetworkTimeout",
            message="Transient timeout connecting to PubMed E-utilities. Applied graceful retry.",
            is_fatal=False,
            degradation_applied=True,
        )

        state["errors"].append(err.model_dump())
        assert len(state["errors"]) == 1
        assert state["errors"][0]["error_type"] == "NetworkTimeout"
        assert state["errors"][0]["degradation_applied"] is True
