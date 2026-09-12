import pytest

from src.agents.evidence_eval import EvidenceEvaluationAgent
from src.domain.enums import (
    WorkflowStage,
    EvidenceType,
    CausalityLevel,
    StudyType,
    DirectionOfEffect,
    DataOrigin,
)
from src.domain.models import EvidenceItem, CitationReference
from src.domain.state import create_initial_state


@pytest.fixture
def evidence_agent():
    return EvidenceEvaluationAgent()


class TestEvidenceEvaluationAgent:

    def test_literature_cooccurrence_never_causal(self, evidence_agent, sample_citation):
        item = EvidenceItem(
            evidence_id="EV-TEST-01",
            target_symbol="TREM2",
            disease_name="Alzheimer's disease",
            evidence_type=EvidenceType.LITERATURE_COOCCURRENCE,
            causality_level=CausalityLevel.CAUSAL_DEMONSTRATED,  # Over-claimed causality
            study_type=StudyType.IN_VITRO_CELLULAR,
            confidence_score=0.85,
            data_origin=DataOrigin.LITERATURE_RETRIEVAL,
            source_database="PubMed",
            citation=sample_citation,
            extracted_statement="Literature co-occurrence statement.",
        )

        assessed = evidence_agent.evaluate_target_evidence("TREM2", [item])
        assert len(assessed) == 1
        # Causality must be downgraded from CAUSAL to FUNCTIONAL
        assert assessed[0].causality_level == CausalityLevel.FUNCTIONAL_ASSOCIATION

    def test_detect_contradictory_effect_directions(self, evidence_agent, sample_citation):
        # Paper 1 claims protective; Paper 2 claims risk-increasing
        item_protective = EvidenceItem(
            evidence_id="EV-P1",
            target_symbol="TARGET_X",
            disease_name="Alzheimer's disease",
            evidence_type=EvidenceType.LITERATURE_COOCCURRENCE,
            causality_level=CausalityLevel.FUNCTIONAL_ASSOCIATION,
            study_type=StudyType.IN_VIVO_ANIMAL,
            direction=DirectionOfEffect.PROTECTIVE,
            confidence_score=0.8,
            data_origin=DataOrigin.LITERATURE_RETRIEVAL,
            source_database="PubMed",
            citation=sample_citation,
            extracted_statement="Overexpression confers neuroprotection.",
        )

        item_pathogenic = EvidenceItem(
            evidence_id="EV-P2",
            target_symbol="TARGET_X",
            disease_name="Alzheimer's disease",
            evidence_type=EvidenceType.LITERATURE_COOCCURRENCE,
            causality_level=CausalityLevel.FUNCTIONAL_ASSOCIATION,
            study_type=StudyType.IN_VIVO_ANIMAL,
            direction=DirectionOfEffect.RISK_INCREASING,
            confidence_score=0.8,
            data_origin=DataOrigin.LITERATURE_RETRIEVAL,
            source_database="PubMed",
            citation=sample_citation,
            extracted_statement="Elevated levels accelerate cognitive decline.",
        )

        assessed = evidence_agent.evaluate_target_evidence("TARGET_X", [item_protective, item_pathogenic])
        assert len(assessed) == 2
        for item in assessed:
            assert item.is_contradictory is True
            assert item.causality_level == CausalityLevel.CONTRADICTORY_EVIDENCE

    def test_concordant_evidence_not_flagged(self, evidence_agent, sample_citation):
        item1 = EvidenceItem(
            evidence_id="EV-C1",
            target_symbol="TREM2",
            disease_name="Alzheimer's disease",
            evidence_type=EvidenceType.GENETIC_ASSOCIATION,
            causality_level=CausalityLevel.CAUSAL_DEMONSTRATED,
            study_type=StudyType.HUMAN_GWAS,
            direction=DirectionOfEffect.RISK_INCREASING,
            confidence_score=0.95,
            data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
            source_database="OpenTargets",
            citation=sample_citation,
            extracted_statement="R47H variant increases risk.",
        )
        item2 = EvidenceItem(
            evidence_id="EV-C2",
            target_symbol="TREM2",
            disease_name="Alzheimer's disease",
            evidence_type=EvidenceType.LITERATURE_COOCCURRENCE,
            causality_level=CausalityLevel.FUNCTIONAL_ASSOCIATION,
            study_type=StudyType.IN_VITRO_CELLULAR,
            direction=DirectionOfEffect.RISK_INCREASING,
            confidence_score=0.80,
            data_origin=DataOrigin.LITERATURE_RETRIEVAL,
            source_database="PubMed",
            citation=sample_citation,
            extracted_statement="Impaired signaling exacerbates pathology.",
        )

        assessed = evidence_agent.evaluate_target_evidence("TREM2", [item1, item2])
        for item in assessed:
            assert item.is_contradictory is False

    def test_run_updates_state_and_preserves_provenance(self, evidence_agent, sample_citation):
        state = create_initial_state(
            session_id="SESS-EV-EVAL",
            research_question="Query",
            disease_name="Alzheimer's",
        )
        raw_item = EvidenceItem(
            evidence_id="EV-PROV-1",
            target_symbol="APP",
            disease_name="Alzheimer's",
            evidence_type=EvidenceType.GENETIC_ASSOCIATION,
            causality_level=CausalityLevel.CAUSAL_DEMONSTRATED,
            study_type=StudyType.HUMAN_GWAS,
            confidence_score=0.95,
            data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
            source_database="OpenTargets",
            citation=sample_citation,
            extracted_statement="Direct causal mutation.",
        )
        state["evidence_records"] = [raw_item.model_dump()]

        updated = evidence_agent.run(state)

        assert updated["current_stage"] == WorkflowStage.EVIDENCE_EVALUATION.value
        assert len(updated["evidence_records"]) == 1
        ev = updated["evidence_records"][0]
        # Provenance verification
        assert ev["citation"]["pmid"] == sample_citation.pmid
        assert ev["citation"]["doi"] == sample_citation.doi
        assert ev["data_origin"] == "experimentally_measured"
        assert len(updated["audit_trace"]) == 1
