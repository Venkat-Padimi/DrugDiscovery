import pytest

from src.domain.state import create_initial_state
from src.engine.reporter import generate_research_report, report_to_markdown, report_to_json


@pytest.fixture
def populated_state_fixture():
    state = create_initial_state(
        session_id="SESS-REP-01",
        research_question="Identify promising therapeutic targets for Alzheimer's disease.",
        disease_name="Alzheimer's disease",
    )
    state["executive_summary"] = "Investigation prioritized TREM2 as top candidate."
    state["target_rankings"] = [
        {
            "target_symbol": "TREM2",
            "target_name": "triggering receptor expressed on myeloid cells 2",
            "disease_name": "Alzheimer's disease",
            "overall_priority_score": 88.5,
            "confidence_tier": "high",
            "confidence_score": 0.90,
            "evidence_count": 3,
            "key_pmids": ["31234567"],
            "strengths": ["Strong human GWAS signal."],
            "limitations": ["Requires BBB delivery."],
            "experimental_validation_status": "Validated",
            "tractability_summary": "Antibody Clinical Precedence",
            "score_breakdown": {
                "disease_association_score": 90.0,
                "genetic_evidence_score": 95.0,
                "target_tractability_score": 90.0,
                "literature_evidence_score": 85.0,
                "experimental_validation_score": 80.0,
                "safety_profile_score": 90.0,
                "contradiction_penalty": 0.0,
                "weights_applied": {
                    "disease_association": 0.25,
                    "genetic_evidence": 0.20,
                    "target_tractability": 0.20,
                    "literature_evidence": 0.15,
                    "experimental_validation": 0.10,
                    "safety_profile": 0.10,
                },
                "raw_composite_score": 89.25,
                "final_clamped_score": 88.5,
            },
        }
    ]
    state["retrieved_papers"] = [
        {
            "pmid": "31234567",
            "doi": "10.1038/s41586-019-1234-5",
            "title": "Microglial TREM2 activation restores cognitive deficits",
            "citation": {
                "pmid": "31234567",
                "doi": "10.1038/s41586-019-1234-5",
                "title": "Microglial TREM2 activation restores cognitive deficits",
                "authors": ["Smith J", "Doe J"],
                "publication_year": 2019,
            },
        }
    ]
    state["known_active_compounds"] = {
        "TREM2": [
            {
                "compound_id": "CHEMBL4298123",
                "compound_name": "TREM2-LIGAND-1",
                "activity_type": "Ki",
                "activity_value": 45.0,
                "activity_unit": "nM",
                "assay_chembl_id": "CHEMBL2837465",
            }
        ]
    }
    state["compound_screenings"] = {
        "TREM2": [
            {
                "compound_id": "REF_PROBE_01_TREM2",
                "predicted_binding_affinity_kcal_mol": -7.5,
                "predicted_kd_nm": 3150.0,
                "molecular_weight": 180.2,
                "logp": 1.2,
            }
        ]
    }
    return state


class TestResearchReporter:

    def test_generate_research_report(self, populated_state_fixture):
        report = generate_research_report(populated_state_fixture)

        assert report.report_id.startswith("REP-")
        assert report.session_id == "SESS-REP-01"
        assert report.disease_name == "Alzheimer's disease"
        assert len(report.top_targets) == 1
        assert report.top_targets[0].target_symbol == "TREM2"
        assert len(report.all_citations) == 1
        assert report.all_citations[0].pmid == "31234567"

    def test_report_to_markdown_structure_and_disclaimers(self, populated_state_fixture):
        report = generate_research_report(populated_state_fixture)
        md = report_to_markdown(report, state=populated_state_fixture)

        assert "# Therapeutic Target Prioritization Report: Alzheimer's disease" in md
        assert "## 1. Executive Summary" in md
        assert "## 2. Prioritized Candidate Targets" in md
        assert "TREM2" in md
        assert "88.5" in md
        assert "## 3. Detailed Target Evaluations" in md
        assert "Deterministic Score Breakdown" in md
        assert "## 4. Platform Methodology" in md
        assert "## 5. Bibliographic Provenance & Citations" in md
        assert "31234567" in md
        assert "## 6. Scientific Integrity & Disclaimers" in md
        assert "Platform Limitations Disclaimer" in md
        assert "Synthetic Assay Notice" in md
        # Check compound screening disclaimer
        assert "Computational simulation prediction — not experimentally measured." in md

    def test_report_to_json(self, populated_state_fixture):
        report = generate_research_report(populated_state_fixture)
        json_str = report_to_json(report)

        assert '"report_id":' in json_str
        assert '"TREM2"' in json_str
        assert '"31234567"' in json_str

    def test_empty_state_report(self):
        empty_state = create_initial_state(
            session_id="SESS-EMPTY-REP",
            research_question="Query for unknown disease",
            disease_name="Unknown Disease",
        )
        report = generate_research_report(empty_state)
        md = report_to_markdown(report, state=empty_state)

        assert report.top_targets == []
        assert "No candidate targets met the threshold" in md
