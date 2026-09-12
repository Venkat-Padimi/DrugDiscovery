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
