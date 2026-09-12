from unittest.mock import MagicMock
import pytest

from src.agents.druggability import DruggabilityAgent
from src.clients.open_targets import OpenTargetsClient, OpenTargetsApiError
from src.domain.enums import WorkflowStage, TractabilityModality, TractabilityBucket, DataOrigin
from src.domain.models import DruggabilityProfile, DruggabilityModalityDetail
from src.domain.state import create_initial_state


@pytest.fixture
def mock_ot_client():
    client = MagicMock(spec=OpenTargetsClient)

    def tractability_mock(ensembl_id, symbol=""):
        if "0095977" in ensembl_id or symbol == "TREM2":
            return DruggabilityProfile(
                target_symbol="TREM2",
                modalities={
                    TractabilityModality.ANTIBODY: DruggabilityModalityDetail(
                        modality=TractabilityModality.ANTIBODY,
                        bucket=TractabilityBucket.CLINICAL_PRECEDENCE,
                        score=90.0,
                        details="Phase II clinical candidate (AL002).",
                    ),
                    TractabilityModality.SMALL_MOLECULE: DruggabilityModalityDetail(
                        modality=TractabilityModality.SMALL_MOLECULE,
                        bucket=TractabilityBucket.DISCOVERY_PRECEDENCE,
                        score=70.0,
                        details="Small molecule tool compound precedence.",
                    ),
                },
                overall_tractability_score=90.0,
                has_small_molecule_binder=True,
                has_approved_drug=False,
                data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
            )
        elif "186318" in ensembl_id or symbol == "BACE1":
            return DruggabilityProfile(
                target_symbol="BACE1",
                modalities={
                    TractabilityModality.SMALL_MOLECULE: DruggabilityModalityDetail(
                        modality=TractabilityModality.SMALL_MOLECULE,
                        bucket=TractabilityBucket.CLINICAL_PRECEDENCE,
                        score=95.0,
                        details="Small molecule clinical precedence.",
                    )
                },
                overall_tractability_score=95.0,
                has_small_molecule_binder=True,
                has_approved_drug=False,
                data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
            )
        return DruggabilityProfile(
            target_symbol=symbol or "UNKNOWN",
            overall_tractability_score=35.0,
            data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
        )

    client.get_target_tractability.side_effect = tractability_mock
    return client


class TestDruggabilityAgent:

    def test_evaluate_target_multiple_modalities(self, mock_ot_client):
        agent = DruggabilityAgent(open_targets_client=mock_ot_client)
        profile = agent.evaluate_target_tractability("TREM2", "ENSG00000095977")

        assert profile.target_symbol == "TREM2"
        assert profile.overall_tractability_score == 90.0
        assert TractabilityModality.ANTIBODY in profile.modalities
        assert TractabilityModality.SMALL_MOLECULE in profile.modalities
        assert profile.modalities[TractabilityModality.ANTIBODY].bucket == TractabilityBucket.CLINICAL_PRECEDENCE
        assert profile.data_origin == DataOrigin.EXPERIMENTALLY_MEASURED

    def test_evaluate_target_unmapped_ensembl_id(self):
        # Open Targets client should not even be called if unmapped
        mock_client = MagicMock(spec=OpenTargetsClient)
        agent = DruggabilityAgent(open_targets_client=mock_client)

        profile = agent.evaluate_target_tractability("UNKNOWN_GENE_999", ensembl_id=None)
        assert profile.overall_tractability_score == 25.0
        assert "incomplete tractability" in profile.summary_rationale.lower()
        mock_client.get_target_tractability.assert_not_called()

    def test_evaluate_target_api_error_degradation(self):
        failing_client = MagicMock(spec=OpenTargetsClient)
        failing_client.get_target_tractability.side_effect = OpenTargetsApiError("Gateway timeout")

        agent = DruggabilityAgent(open_targets_client=failing_client)
        profile = agent.evaluate_target_tractability("TREM2", "ENSG00000095977")

        assert profile.target_symbol == "TREM2"
        assert profile.overall_tractability_score == 30.0
        assert "degraded" in profile.summary_rationale.lower()

    def test_run_updates_state_and_records_trace(self, mock_ot_client):
        agent = DruggabilityAgent(open_targets_client=mock_ot_client)
        state = create_initial_state(
            session_id="SESS-DRUG-01",
            research_question="Query",
            disease_name="Alzheimer's disease",
        )
        state["identified_targets"] = {
            "TREM2": {"target_symbol": "TREM2", "ensembl_id": "ENSG00000095977"},
            "BACE1": {"target_symbol": "BACE1", "ensembl_id": "ENSG00000186318"},
        }

        updated = agent.run(state)

        assert updated["current_stage"] == WorkflowStage.TRACTABILITY_ASSESSMENT.value
        assert "TREM2" in updated["druggability_assessments"]
        assert "BACE1" in updated["druggability_assessments"]
        assert updated["druggability_assessments"]["TREM2"]["overall_tractability_score"] == 90.0
        assert len(updated["audit_trace"]) == 1

    def test_run_empty_targets_handles_gracefully(self, mock_ot_client):
        agent = DruggabilityAgent(open_targets_client=mock_ot_client)
        state = create_initial_state(
            session_id="SESS-EMPTY",
            research_question="Query",
            disease_name="Alzheimer's",
        )
        state["identified_targets"] = {}

        updated = agent.run(state)
        assert len(updated["druggability_assessments"]) == 0
        assert updated["audit_trace"][0]["status"] == "degraded"
