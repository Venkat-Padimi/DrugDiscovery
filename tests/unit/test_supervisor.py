import pytest

from src.agents.supervisor import SupervisorAgent
from src.domain.enums import WorkflowStage
from src.domain.state import create_initial_state


class TestSupervisorAgent:

    @pytest.fixture
    def supervisor(self):
        return SupervisorAgent()

    def test_extract_disease_name_from_question(self, supervisor):
        q1 = "Identify promising therapeutic targets for Alzheimer's disease."
        assert "Alzheimer" in supervisor.extract_disease_name_from_question(q1)

        q2 = "Find novel targets for Parkinson's disease"
        assert "Parkinson" in supervisor.extract_disease_name_from_question(q2)

        q3 = "Targeting Amyotrophic lateral sclerosis"
        assert "Amyotrophic lateral sclerosis" in supervisor.extract_disease_name_from_question(q3)

    def test_plan_initializes_investigation(self, supervisor):
        state = create_initial_state(
            session_id="SESS-SUP-01",
            research_question="Identify therapeutic targets for Alzheimer's disease",
            disease_name="",
        )

        planned_state = supervisor.plan(state)

        assert planned_state["status"] == "in_progress"
        assert planned_state["current_stage"] == WorkflowStage.INITIALIZATION.value
        assert "Alzheimer" in planned_state["disease_name"]
        assert len(planned_state["audit_trace"]) == 1
        assert planned_state["audit_trace"][0]["agent_name"] == "SupervisorAgent"

    def test_synthesize_with_ranked_targets(self, supervisor):
        state = create_initial_state(
            session_id="SESS-SUP-02",
            research_question="Identify targets for Alzheimer's",
            disease_name="Alzheimer's disease",
        )
        state["target_rankings"] = [
            {
                "target_symbol": "TREM2",
                "overall_priority_score": 88.5,
                "confidence_tier": "high",
                "key_pmids": ["31234567"],
                "strengths": ["Strong genetic support in human GWAS."],
            },
            {
                "target_symbol": "BACE1",
                "overall_priority_score": 82.0,
                "confidence_tier": "high",
                "key_pmids": ["32345678"],
                "strengths": ["High tractability with small molecule inhibitors."],
            },
        ]

        synthesized = supervisor.synthesize(state)

        assert synthesized["current_stage"] == WorkflowStage.COMPLETED.value
        assert synthesized["status"] == "completed"
        assert synthesized["executive_summary"] is not None
        assert "TREM2" in synthesized["executive_summary"]
        assert "88.5" in synthesized["executive_summary"]
        assert "BACE1" in synthesized["executive_summary"]
        assert "synthetic demonstration" in synthesized["executive_summary"].lower()

    def test_synthesize_with_empty_targets(self, supervisor):
        state = create_initial_state(
            session_id="SESS-SUP-EMPTY",
            research_question="Identify targets for unknown disease",
            disease_name="RareUnknownCondition",
        )
        state["target_rankings"] = []

        synthesized = supervisor.synthesize(state)

        assert synthesized["current_stage"] == WorkflowStage.COMPLETED.value
        assert "insufficient evidence" in synthesized["executive_summary"].lower()
