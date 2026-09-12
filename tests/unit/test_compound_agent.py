import pytest
from unittest.mock import MagicMock

from src.agents.compound import CompoundScreeningAgent
from src.clients.chembl import ChEMBLClient, ChEMBLApiError
from src.domain.enums import WorkflowStage, DataOrigin
from src.domain.models import CompoundBioactivity, ScreeningPrediction
from src.domain.state import create_initial_state
from src.engine.screening import PhysicochemicalSimulationEngine


@pytest.fixture
def mock_chembl_client():
    client = MagicMock(spec=ChEMBLClient)

    def search_target_mock(symbol: str):
        if symbol == "BACE1":
            return "CHEMBL2487"
        elif symbol == "TREM2":
            return "CHEMBL4822"
        return None

    def get_bioactivities_mock(target_chembl_id: str, target_symbol: str = "", limit: int = 10):
        if target_chembl_id == "CHEMBL2487":
            return [
                CompoundBioactivity(
                    compound_id="CHEMBL3545112",
                    compound_name="VERUBECESTAT",
                    smiles="CS(=O)(=O)c1ccc(cc1)C1(N=C(N)c2c1cc(F)cc2)c1ccc(F)cn1",
                    target_symbol="BACE1",
                    activity_type="IC50",
                    activity_value=2.2,
                    activity_unit="nM",
                    assay_chembl_id="CHEMBL1928374",
                    data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
                )
            ]
        elif target_chembl_id == "CHEMBL4822":
            return [
                CompoundBioactivity(
                    compound_id="CHEMBL4298123",
                    compound_name="TREM2-LIGAND-1",
                    smiles="CC(C)Cc1ccc(cc1)C(C)C(=O)O",
                    target_symbol="TREM2",
                    activity_type="Ki",
                    activity_value=45.0,
                    activity_unit="nM",
                    assay_chembl_id="CHEMBL2837465",
                    data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
                )
            ]
        return []

    client.search_target.side_effect = search_target_mock
    client.get_target_bioactivities.side_effect = get_bioactivities_mock
    return client


class TestCompoundScreeningAgent:

    def test_compound_screening_disabled_skips_cleanly(self, mock_chembl_client):
        agent = CompoundScreeningAgent(chembl_client=mock_chembl_client)
        state = create_initial_state(
            session_id="SESS-CMPD-01",
            research_question="Query with screening disabled",
            disease_name="Alzheimer's disease",
            enable_compound_screening=False,
        )

        result_state = agent.run(state)

        assert result_state["current_stage"] == WorkflowStage.COMPOUND_SCREENING.value
        assert mock_chembl_client.search_target.call_count == 0
        assert any("disabled in state" in t.get("input_summary", "") for t in result_state["audit_trace"])

    def test_compound_screening_no_targets_handles_degraded(self, mock_chembl_client):
        agent = CompoundScreeningAgent(chembl_client=mock_chembl_client)
        state = create_initial_state(
            session_id="SESS-CMPD-EMPTY",
            research_question="No targets found",
            disease_name="Unknown disease",
            enable_compound_screening=True,
        )
        state["target_rankings"] = []
        state["identified_targets"] = {}

        result_state = agent.run(state)

        assert result_state["current_stage"] == WorkflowStage.COMPOUND_SCREENING.value
        assert result_state["known_active_compounds"] == {}
        assert result_state["compound_screenings"] == {}
        trace = result_state["audit_trace"][-1]
        assert trace["status"] == "degraded"
        assert "No targets available" in trace["input_summary"]

    def test_compound_screening_successful_run(self, mock_chembl_client):
        agent = CompoundScreeningAgent(chembl_client=mock_chembl_client)
        state = create_initial_state(
            session_id="SESS-CMPD-SUCCESS",
            research_question="Identify compounds for BACE1 and TREM2",
            disease_name="Alzheimer's disease",
            enable_compound_screening=True,
        )
        state["target_rankings"] = [
            {"target_symbol": "BACE1", "overall_priority_score": 90.0},
            {"target_symbol": "TREM2", "overall_priority_score": 85.0},
        ]

        result_state = agent.run(state)

        # 1. State integrity
        assert result_state["current_stage"] == WorkflowStage.COMPOUND_SCREENING.value
        assert "BACE1" in result_state["known_active_compounds"]
        assert "TREM2" in result_state["known_active_compounds"]
        assert "BACE1" in result_state["compound_screenings"]
        assert "TREM2" in result_state["compound_screenings"]

        # 2. Measured bioactivities validation (DataOrigin.EXPERIMENTALLY_MEASURED)
        bace1_measured = result_state["known_active_compounds"]["BACE1"]
        assert len(bace1_measured) == 1
        assert bace1_measured[0]["compound_id"] == "CHEMBL3545112"
        assert bace1_measured[0]["activity_type"] == "IC50"
        assert bace1_measured[0]["activity_value"] == 2.2
        assert bace1_measured[0]["data_origin"] == DataOrigin.EXPERIMENTALLY_MEASURED

        # 3. In silico screening validation (DataOrigin.COMPUTATIONAL_PREDICTION + disclaimer)
        bace1_screened = result_state["compound_screenings"]["BACE1"]
        assert len(bace1_screened) >= 1
        for pred in bace1_screened:
            assert pred["data_origin"] == DataOrigin.COMPUTATIONAL_PREDICTION
            assert pred["disclaimer"] == "Computational simulation prediction — not experimentally measured."
            assert pred["predicted_binding_affinity_kcal_mol"] is not None
            assert pred["predicted_kd_nm"] is not None
            assert pred["confidence_interval"] is not None
            assert len(pred["confidence_interval"]) == 2

        # 4. Audit trace validation
        trace = result_state["audit_trace"][-1]
        assert trace["agent_name"] == "CompoundScreeningAgent"
        assert trace["status"] == "success"
        assert "Retrieved 2 measured bioactivities" in trace["output_summary"]

    def test_chembl_api_error_records_degradation_without_halting(self):
        failing_client = MagicMock(spec=ChEMBLClient)
        failing_client.search_target.side_effect = ChEMBLApiError("ChEMBL server down 503")

        agent = CompoundScreeningAgent(chembl_client=failing_client)
        state = create_initial_state(
            session_id="SESS-CMPD-ERR",
            research_question="Error handling test",
            disease_name="Alzheimer's disease",
            enable_compound_screening=True,
        )
        state["target_rankings"] = [{"target_symbol": "BACE1", "overall_priority_score": 85.0}]

        result_state = agent.run(state)

        # Verified pipeline continues
        assert result_state["current_stage"] == WorkflowStage.COMPOUND_SCREENING.value
        assert result_state["known_active_compounds"]["BACE1"] == []
        # In silico simulation fallback executes on benchmark probes
        assert len(result_state["compound_screenings"]["BACE1"]) >= 1
        assert any(e["error_type"] == "ChEMBLApiError" for e in result_state["errors"])
        assert any(e["degradation_applied"] is True for e in result_state["errors"])

    def test_deterministic_screening_reproducibility(self, mock_chembl_client):
        agent = CompoundScreeningAgent(chembl_client=mock_chembl_client)
        engine = PhysicochemicalSimulationEngine()

        smiles = "CC(=O)Oc1ccccc1C(=O)O"
        pred1 = engine.predict_affinity(target_symbol="BACE1", smiles=smiles)
        pred2 = engine.predict_affinity(target_symbol="BACE1", smiles=smiles)

        assert pred1.predicted_binding_affinity_kcal_mol == pred2.predicted_binding_affinity_kcal_mol
        assert pred1.predicted_kd_nm == pred2.predicted_kd_nm
        assert pred1.molecular_weight == pred2.molecular_weight
        assert pred1.logp == pred2.logp
        assert pred1.tpsa == pred2.tpsa
        assert pred1.disclaimer == "Computational simulation prediction — not experimentally measured."
