import pytest

from src.ui.helpers import (
    get_sample_presets,
    format_confidence_badge,
    extract_target_detail,
    filter_audit_trace,
    prepare_rankings_dataframe,
)


class TestUiHelpers:

    def test_sample_presets(self):
        presets = get_sample_presets()
        assert "Custom Query" in presets
        assert "Alzheimer's Disease (TREM2 & BACE1)" in presets
        assert "Parkinson's Disease (SNCA & LRRK2)" in presets
        for name, data in presets.items():
            assert "question" in data
            assert "disease_name" in data

    def test_format_confidence_badge(self):
        assert "High" in format_confidence_badge("high")
        assert "Medium" in format_confidence_badge("medium")
        assert "Low" in format_confidence_badge("low")
        assert "Unconfirmed" in format_confidence_badge("unknown")

    def test_extract_target_detail(self):
        state = {
            "identified_targets": {
                "TREM2": {"target_symbol": "TREM2", "ensembl_id": "ENSG00000095977"}
            },
            "target_rankings": [
                {"target_symbol": "TREM2", "overall_priority_score": 88.5}
            ],
            "evidence_records": [
                {"target_symbol": "TREM2", "evidence_type": "genetic_association"}
            ],
            "druggability_assessments": {
                "TREM2": {"overall_tractability_score": 90.0}
            },
            "experimental_data_matches": {
                "TREM2": [{"record_id": "EXP-01", "assay_type": "CRISPR"}]
            },
            "known_active_compounds": {
                "TREM2": [{"compound_id": "CHEMBL1"}]
            },
            "compound_screenings": {
                "TREM2": [{"compound_id": "SIM-01"}]
            },
        }

        detail = extract_target_detail(state, "TREM2")
        assert detail["target_symbol"] == "TREM2"
        assert detail["metadata"]["ensembl_id"] == "ENSG00000095977"
        assert detail["ranking"]["overall_priority_score"] == 88.5
        assert len(detail["evidence"]) == 1
        assert detail["druggability"]["overall_tractability_score"] == 90.0
        assert len(detail["experimental"]) == 1
        assert len(detail["known_compounds"]) == 1
        assert len(detail["simulated_compounds"]) == 1

    def test_extract_target_detail_empty_symbol(self):
        assert extract_target_detail({}, "") == {}

    def test_filter_audit_trace(self):
        trace = [
            {"agent_name": "SupervisorAgent", "step": 1},
            {"agent_name": "LiteratureSearchAgent", "step": 2},
            {"agent_name": "SupervisorAgent", "step": 3},
        ]
        assert len(filter_audit_trace(trace, "All Agents")) == 3
        assert len(filter_audit_trace(trace, None)) == 3
        sup_trace = filter_audit_trace(trace, "SupervisorAgent")
        assert len(sup_trace) == 2
        assert all(t["agent_name"] == "SupervisorAgent" for t in sup_trace)

    def test_prepare_rankings_dataframe(self):
        rankings = [
            {
                "target_symbol": "BACE1",
                "target_name": "Beta-secretase 1",
                "overall_priority_score": 85.34,
                "confidence_tier": "high",
                "tractability_summary": "Clinical Precedence",
                "experimental_validation_status": "Assay-Validated",
                "evidence_count": 5,
            }
        ]
        rows = prepare_rankings_dataframe(rankings)
        assert len(rows) == 1
        row = rows[0]
        assert row["Rank"] == "#1"
        assert row["Symbol"] == "BACE1"
        assert row["Priority Score"] == 85.3
        assert row["Confidence Tier"] == "HIGH"
