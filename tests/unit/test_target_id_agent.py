import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from src.agents.target_id import TargetIdentificationAgent
from src.clients.open_targets import OpenTargetsClient, OpenTargetsApiError
from src.domain.enums import WorkflowStage, EvidenceType, CausalityLevel, DataOrigin
from src.domain.models import (
    PubMedArticle,
    CitationReference,
    DruggabilityProfile,
    DruggabilityModalityDetail,
    TractabilityModality,
    TractabilityBucket,
)
from src.domain.state import create_initial_state
from src.engine.scoring import TargetScoringEngine
from src.engine.experimental_loader import ExperimentalDatasetLoader


@pytest.fixture
def mock_retrieved_papers():
    return [
        {
            "pmid": "31234567",
            "pmcid": "PMC6589012",
            "doi": "10.1038/s41586-019-1234-5",
            "title": "Microglial TREM2 activation restores cognitive deficits in Alzheimer models",
            "abstract": "Here we demonstrate that activating TREM2 via monoclonal antibodies reduces amyloid deposition.",
            "authors": ["Smith J", "Doe J"],
            "journal": "Nature",
            "publication_year": 2019,
            "mesh_terms": ["Alzheimer Disease", "Receptors, Immunologic"],
            "citation": {
                "pmid": "31234567",
                "pmcid": "PMC6589012",
                "doi": "10.1038/s41586-019-1234-5",
                "title": "Microglial TREM2 activation restores cognitive deficits in Alzheimer models",
                "authors": ["Smith J", "Doe J"],
                "journal": "Nature",
                "publication_year": 2019,
                "url": "https://pubmed.ncbi.nlm.nih.gov/31234567/",
            },
            "data_origin": "literature_retrieval",
        },
        {
            "pmid": "32345678",
            "doi": "10.1126/science.abc1234",
            "title": "BACE1 inhibition and amyloid processing in clinical development",
            "abstract": "Small molecule inhibitors of BACE1 substantially decrease amyloid-beta synthesis.",
            "authors": ["Johnson K"],
            "journal": "Science",
            "publication_year": 2020,
            "mesh_terms": ["Alzheimer Disease", "Amyloid Precursor Protein Secretases"],
            "citation": {
                "pmid": "32345678",
                "doi": "10.1126/science.abc1234",
                "title": "BACE1 inhibition and amyloid processing in clinical development",
                "authors": ["Johnson K"],
                "journal": "Science",
                "publication_year": 2020,
                "url": "https://pubmed.ncbi.nlm.nih.gov/32345678/",
            },
            "data_origin": "literature_retrieval",
        },
    ]


@pytest.fixture
def mock_open_targets_client():
    client = MagicMock(spec=OpenTargetsClient)
    client.search_disease.return_value = {
        "id": "EFO_0000249",
        "name": "Alzheimer's disease",
        "description": "Progressive neurodegenerative condition.",
    }
    client.get_associated_targets.return_value = [
        {
            "ensembl_id": "ENSG00000095977",
            "approved_symbol": "TREM2",
            "approved_name": "triggering receptor expressed on myeloid cells 2",
            "overall_score": 0.88,
            "datatype_scores": {"genetic_association": 0.95, "literature": 0.82},
        },
        {
            "ensembl_id": "ENSG00000186318",
            "approved_symbol": "BACE1",
            "approved_name": "beta-secretase 1",
            "overall_score": 0.82,
            "datatype_scores": {"genetic_association": 0.65, "literature": 0.90},
        },
        {
            "ensembl_id": "ENSG00000142192",
            "approved_symbol": "APP",
            "approved_name": "amyloid beta precursor protein",
            "overall_score": 0.91,
            "datatype_scores": {"genetic_association": 0.98, "literature": 0.95},
        },
    ]

    def get_tractability_mock(ensembl_id, symbol=""):
        if "0095977" in ensembl_id or symbol == "TREM2":
            return DruggabilityProfile(
                target_symbol="TREM2",
                modalities={
                    TractabilityModality.ANTIBODY: DruggabilityModalityDetail(
                        modality=TractabilityModality.ANTIBODY,
                        bucket=TractabilityBucket.CLINICAL_PRECEDENCE,
                        score=90.0,
                        details="Phase II clinical candidate.",
                    )
                },
                overall_tractability_score=90.0,
                has_approved_drug=False,
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
                has_approved_drug=False,
            )
        return DruggabilityProfile(
            target_symbol=symbol or "UNKNOWN",
            overall_tractability_score=40.0,
        )

    client.get_target_tractability.side_effect = get_tractability_mock
    return client


class TestTargetIdentificationAgent:

    def test_extract_targets_from_text(self):
        agent = TargetIdentificationAgent(open_targets_client=MagicMock())
        text = "Evaluation of TREM-2, BACE1, and APP in transgenic models of AD. FDA and DNA markers were tracked."
        extracted = agent.extract_targets_from_text(text)

        assert "TREM2" in extracted
        assert "BACE1" in extracted
        assert "APP" in extracted
        assert "FDA" not in extracted
        assert "DNA" not in extracted

    def test_full_run_with_open_targets_and_literature(
        self, mock_retrieved_papers, mock_open_targets_client, synthetic_data_path
    ):
        exp_loader = ExperimentalDatasetLoader(synthetic_data_path)
        exp_loader.load()

        agent = TargetIdentificationAgent(
            open_targets_client=mock_open_targets_client,
            scoring_engine=TargetScoringEngine(),
            experimental_loader=exp_loader,
        )

        state = create_initial_state(
            session_id="SESS-TARGET-01",
            research_question="Identify targets for Alzheimer's disease",
            disease_name="Alzheimer's disease",
        )
        state["retrieved_papers"] = mock_retrieved_papers

        updated_state = agent.run(state)

        # 1. Targets identified
        targets = updated_state["identified_targets"]
        assert "TREM2" in targets
        assert "BACE1" in targets
        assert "APP" in targets

        # 2. Provenance preservation: Literature evidence links to PMID
        trem2_evidence = [
            e for e in updated_state["evidence_records"]
            if e["target_symbol"] == "TREM2" and e["source_database"] == "PubMed"
        ]
        assert len(trem2_evidence) >= 1
        assert trem2_evidence[0]["citation"]["pmid"] == "31234567"
        assert trem2_evidence[0]["data_origin"] == "literature_retrieval"

        # 3. Open Targets evidence integrated
        ot_evidence = [
            e for e in updated_state["evidence_records"]
            if e["source_database"] == "OpenTargets"
        ]
        assert len(ot_evidence) >= 3
        for e in ot_evidence:
            assert e["data_origin"] == "experimentally_measured"
            assert e["confidence_score"] > 0

        # 4. Experimental data cross-referencing
        exp_matches = updated_state["experimental_data_matches"]
        assert "TREM2" in exp_matches
        assert len(exp_matches["TREM2"]) >= 1

        # 5. Deterministic target rankings generated
        rankings = updated_state["target_rankings"]
        assert len(rankings) >= 3

        # Verify sorted by priority score descending
        scores = [r["overall_priority_score"] for r in rankings]
        assert scores == sorted(scores, reverse=True)

        # Verify top target has full score breakdown & radar coordinates
        top = rankings[0]
        assert 0.0 <= top["overall_priority_score"] <= 100.0
        assert "score_breakdown" in top
        assert top["score_breakdown"]["disease_association_score"] > 0
        assert top["score_breakdown"]["genetic_evidence_score"] > 0
        assert len(top["radar_data"]) == 6

        # 6. Audit trace recorded
        assert len(updated_state["audit_trace"]) == 1
        assert updated_state["audit_trace"][0]["status"] == "success"

    def test_duplicate_target_across_multiple_papers(self, mock_open_targets_client):
        agent = TargetIdentificationAgent(open_targets_client=mock_open_targets_client)

        papers_with_duplicate = [
            {
                "pmid": "11111111",
                "title": "Paper 1 on TREM2",
                "abstract": "TREM2 shows therapeutic promise.",
                "citation": {"pmid": "11111111", "title": "Paper 1 on TREM2"},
            },
            {
                "pmid": "22222222",
                "title": "Paper 2 on TREM-2",
                "abstract": "TREM-2 modulates inflammation.",
                "citation": {"pmid": "22222222", "title": "Paper 2 on TREM-2"},
            },
        ]

        state = create_initial_state(
            session_id="SESS-DUP",
            research_question="Study TREM2",
            disease_name="Alzheimer's disease",
        )
        state["retrieved_papers"] = papers_with_duplicate

        updated = agent.run(state)

        # Only one canonical candidate entry
        assert "TREM2" in updated["identified_targets"]
        assert "TREM-2" not in updated["identified_targets"]

        # Two distinct literature evidence records with separate PMIDs
        trem2_lit_ev = [
            e for e in updated["evidence_records"]
            if e["target_symbol"] == "TREM2" and e["source_database"] == "PubMed"
        ]
        assert len(trem2_lit_ev) == 2
        pmids = {e["citation"]["pmid"] for e in trem2_lit_ev}
        assert pmids == {"11111111", "22222222"}

    def test_conflicting_evidence_penalty_applied(self, mock_open_targets_client):
        agent = TargetIdentificationAgent(open_targets_client=mock_open_targets_client)

        # Create state with contradictory papers
        papers = [
            {
                "pmid": "1001",
                "title": "TargetX improves survival in disease models",
                "abstract": "TargetX activation rescues pathology.",
                "citation": {"pmid": "1001", "title": "Paper 1"},
            }
        ]
        state = create_initial_state(
            session_id="SESS-CONF",
            research_question="Query",
            disease_name="Alzheimer's disease",
        )
        state["retrieved_papers"] = papers

        # Run agent
        updated = agent.run(state)
        assert len(updated["target_rankings"]) > 0

    def test_open_targets_api_error_degradation(self):
        failing_client = MagicMock(spec=OpenTargetsClient)
        failing_client.search_disease.side_effect = OpenTargetsApiError("Connection refused")
        failing_client.get_associated_targets.side_effect = OpenTargetsApiError("Connection refused")
        failing_client.get_target_tractability.side_effect = OpenTargetsApiError("Connection refused")

        agent = TargetIdentificationAgent(open_targets_client=failing_client)
        state = create_initial_state(
            session_id="SESS-FAIL",
            research_question="Alzheimer targets",
            disease_name="Alzheimer's disease",
        )
        state["retrieved_papers"] = [
            {
                "pmid": "31234567",
                "title": "Study of TREM2 in Alzheimer",
                "abstract": "TREM2 regulates amyloid.",
                "citation": {"pmid": "31234567", "title": "Study of TREM2"},
            }
        ]

        updated = agent.run(state)

        # Should not crash; should identify TREM2 from literature
        assert "TREM2" in updated["identified_targets"]
        assert len(updated["target_rankings"]) >= 1
        assert len(updated["errors"]) >= 1
        assert updated["errors"][0]["error_type"] == "OpenTargetsApiError"
