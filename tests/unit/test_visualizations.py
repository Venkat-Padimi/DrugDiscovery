import pytest
import plotly.graph_objects as go

from src.ui.visualizations import (
    render_target_ranking_chart,
    render_radar_chart,
    render_evidence_distribution_chart,
    render_compound_bioactivity_chart,
)


class TestVisualizations:

    def test_render_target_ranking_chart_with_data(self):
        rankings = [
            {"target_symbol": "TREM2", "overall_priority_score": 88.5, "confidence_tier": "high"},
            {"target_symbol": "BACE1", "overall_priority_score": 82.0, "confidence_tier": "high"},
            {"target_symbol": "APP", "overall_priority_score": 75.0, "confidence_tier": "medium"},
        ]
        fig = render_target_ranking_chart(rankings)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        # In horizontal bar chart, y contains symbols, x contains scores
        assert "TREM2" in fig.data[0].y
        assert 88.5 in fig.data[0].x

    def test_render_target_ranking_chart_empty(self):
        assert render_target_ranking_chart([]) is None

    def test_render_radar_chart_with_data(self):
        radar_data = {
            "disease_association": 90.0,
            "genetic_evidence": 85.0,
            "target_tractability": 70.0,
            "literature_evidence": 80.0,
            "experimental_validation": 65.0,
            "safety_profile": 90.0,
        }
        fig = render_radar_chart(radar_data, "TREM2")

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert "Scatterpolar" in str(type(fig.data[0]))
        # 6 dimensions + 1 closed loop item = 7 items
        assert len(fig.data[0].r) == 7

    def test_render_radar_chart_empty(self):
        assert render_radar_chart({}, "TREM2") is None

    def test_render_evidence_distribution_chart(self):
        evidence_items = [
            {"evidence_type": "genetic_association"},
            {"evidence_type": "genetic_association"},
            {"evidence_type": "literature_cooccurrence"},
        ]
        fig = render_evidence_distribution_chart(evidence_items)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert "Pie" in str(type(fig.data[0]))

    def test_render_evidence_distribution_chart_empty(self):
        assert render_evidence_distribution_chart([]) is None

    def test_render_compound_bioactivity_chart_separation(self):
        known = [
            {
                "compound_id": "CHEMBL123",
                "compound_name": "ActiveMolecule",
                "activity_type": "IC50",
                "activity_value": 15.0,
            }
        ]
        simulated = [
            {
                "compound_id": "SIM_001",
                "predicted_kd_nm": 450.0,
            }
        ]

        fig = render_compound_bioactivity_chart(known, simulated, "BACE1")

        assert isinstance(fig, go.Figure)
        # Expect 2 separate bar traces for empirical vs computational
        assert len(fig.data) == 2
        trace_names = [t.name for t in fig.data]
        assert any("Empirical" in name for name in trace_names)
        assert any("Simulation" in name for name in trace_names)

    def test_render_compound_bioactivity_chart_empty(self):
        assert render_compound_bioactivity_chart([], [], "BACE1") is None
