from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.domain.state import create_initial_state


@pytest.fixture
def client():
    return TestClient(app)


class TestFastApiBackend:

    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "Drug Discovery" in data["platform"]
        assert len(data["workflow_stages"]) >= 6

    def test_investigate_endpoint_validation_error(self, client):
        # Missing required research_question field
        resp = client.post("/api/investigate", json={})
        assert resp.status_code == 422

    def test_investigate_endpoint_successful_execution(self, client):
        mock_final_state = create_initial_state(
            session_id="API-TEST-01",
            research_question="Identify targets for Alzheimer's",
            disease_name="Alzheimer's disease",
        )
        mock_final_state["target_rankings"] = [
            {"target_symbol": "TREM2", "overall_priority_score": 88.0, "confidence_tier": "high"}
        ]
        mock_final_state["status"] = "completed"

        with patch("src.api.app.ResearchWorkflowRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner.run.return_value = mock_final_state
            mock_runner_cls.return_value = mock_runner

            payload = {
                "research_question": "Identify targets for Alzheimer's",
                "disease_name": "Alzheimer's disease",
                "enable_compound_screening": True,
                "top_n_targets_to_screen": 3,
            }
            resp = client.post("/api/investigate", json=payload)

            assert resp.status_code == 200
            data = resp.json()
            assert data["session_id"] == "API-TEST-01"
            assert data["status"] == "completed"
            assert len(data["target_rankings"]) == 1
            assert data["target_rankings"][0]["target_symbol"] == "TREM2"

    def test_report_generation_endpoint(self, client):
        state = create_initial_state(
            session_id="API-REP-01",
            research_question="Query for report",
            disease_name="Alzheimer's disease",
        )
        state["target_rankings"] = [
            {
                "target_symbol": "TREM2",
                "disease_name": "Alzheimer's disease",
                "overall_priority_score": 88.0,
                "confidence_tier": "high",
                "confidence_score": 0.9,
                "evidence_count": 2,
                "experimental_validation_status": "Validated",
                "tractability_summary": "Antibody Clinical Precedence",
                "score_breakdown": {
                    "disease_association_score": 90.0,
                    "genetic_evidence_score": 90.0,
                    "target_tractability_score": 90.0,
                    "literature_evidence_score": 80.0,
                    "experimental_validation_score": 80.0,
                    "safety_profile_score": 90.0,
                    "contradiction_penalty": 0.0,
                    "weights_applied": {},
                    "raw_composite_score": 88.0,
                    "final_clamped_score": 88.0,
                },
            }
        ]

        resp = client.post("/api/report", json=state)
        assert resp.status_code == 200
        data = resp.json()
        assert "report" in data
        assert "markdown" in data
        assert "Therapeutic Target Prioritization Report" in data["markdown"]
        assert "TREM2" in data["markdown"]

    def test_presets_endpoint(self, client):
        resp = client.get("/api/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "Alzheimer's Disease (TREM2 & BACE1)" in data
        assert "Parkinson's Disease (SNCA & LRRK2)" in data

    def test_session_detail_and_graph_endpoints(self, client):
        from src.api.app import SESSION_STORE
        mock_state = create_initial_state(
            session_id="API-STORE-TEST",
            research_question="Identify targets for Alzheimer's",
            disease_name="Alzheimer's disease",
        )
        mock_state["target_rankings"] = [
            {
                "target_symbol": "TREM2",
                "target_name": "Triggering Receptor Expressed On Myeloid Cells 2",
                "overall_priority_score": 88.0,
                "confidence_tier": "high",
                "tractability_summary": "Antibody Clinical Precedence",
                "experimental_validation_status": "Validated",
            }
        ]
        mock_state["identified_targets"] = {
            "TREM2": {"symbol": "TREM2", "name": "Triggering Receptor Expressed On Myeloid Cells 2"}
        }
        mock_state["evidence_records"] = [
            {
                "target_symbol": "TREM2",
                "evidence_type": "genetic_association",
                "causality_level": "direct_causal_variant",
                "is_contradictory": False,
                "citation": {"pmid": "31234567", "title": "TREM2 in AD"},
            }
        ]
        mock_state["druggability_assessments"] = {
            "TREM2": {
                "target_symbol": "TREM2",
                "overall_tractability_score": 85.0,
                "modalities": {"Antibody": {"bucket": "Clinical Precedence"}},
            }
        }
        mock_state["known_active_compounds"] = {
            "TREM2": [{"compound_id": "CHEMBL123", "activity_type": "IC50", "activity_value": 15.0}]
        }
        mock_state["compound_screenings"] = {
            "TREM2": [{"compound_id": "SIM_001", "predicted_kd_nm": 42.0}]
        }
        mock_state["audit_trace"] = [
            {"agent_name": "SupervisorAgent", "stage": "supervisor_plan", "output_summary": "Plan made"}
        ]

        SESSION_STORE["API-STORE-TEST"] = mock_state
        SESSION_STORE["latest"] = mock_state

        # Test session list
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert any(s["session_id"] == "API-STORE-TEST" for s in resp.json())

        # Test session get
        resp = client.get("/api/sessions/API-STORE-TEST")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "API-STORE-TEST"

        # Test targets
        resp = client.get("/api/sessions/API-STORE-TEST/targets")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Test target detail
        resp = client.get("/api/sessions/API-STORE-TEST/targets/TREM2")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["target_symbol"] == "TREM2"
        assert len(detail["evidence"]) == 1

        # Test compounds with disclaimer
        resp = client.get("/api/sessions/API-STORE-TEST/compounds")
        assert resp.status_code == 200
        data = resp.json()
        assert "TREM2" in data["known_active_compounds"]
        assert "TREM2" in data["compound_screenings"]
        assert "disclaimer" in data

        # Test evidence
        resp = client.get("/api/sessions/API-STORE-TEST/evidence")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Test audit
        resp = client.get("/api/sessions/API-STORE-TEST/audit")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Test graph
        resp = client.get("/api/sessions/API-STORE-TEST/graph")
        assert resp.status_code == 200
        g = resp.json()
        assert "nodes" in g
        assert "edges" in g
        assert len(g["nodes"]) >= 2

    def test_root_serves_frontend_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "html" in resp.headers.get("content-type", "").lower()
        assert "root" in resp.text

