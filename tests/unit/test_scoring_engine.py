import pytest

from src.domain.enums import (
    EvidenceType,
    CausalityLevel,
    StudyType,
    TractabilityModality,
    TractabilityBucket,
    ConfidenceTier,
    DataOrigin,
)
from src.domain.models import (
    EvidenceItem,
    DruggabilityProfile,
    DruggabilityModalityDetail,
    ExperimentalRecord,
    TargetCandidate,
    CitationReference,
)
from src.engine.scoring import TargetScoringEngine
from config.settings import ScoringWeights


class TestTargetScoringEngine:

    def test_disease_association_with_open_targets_score(self, scoring_engine, sample_evidence_items):
        # Open Targets gives 0.85 -> S_disease = 85.0
        score = scoring_engine.calculate_disease_association_score(
            sample_evidence_items, open_targets_overall_score=0.85
        )
        assert score == 85.0

    def test_disease_association_fallback_without_open_targets(self, scoring_engine, sample_evidence_items):
        score = scoring_engine.calculate_disease_association_score(
            sample_evidence_items, open_targets_overall_score=None
        )
        assert score > 50.0  # Derived from high-confidence genetic item

    def test_genetic_evidence_scoring_with_causal_gwas(self, scoring_engine, sample_evidence_items):
        score = scoring_engine.calculate_genetic_evidence_score(sample_evidence_items)
        # Has causal (60) + gwas_sig (25) + max_conf*15 (14.25) -> capped at 99.25
        assert score >= 90.0

    def test_genetic_evidence_zero_when_no_genetics(self, scoring_engine, sample_citation):
        non_genetic = [
            EvidenceItem(
                evidence_id="EV-NG",
                target_symbol="XYZ",
                disease_name="Disease",
                evidence_type=EvidenceType.LITERATURE_COOCCURRENCE,
                causality_level=CausalityLevel.STATISTICAL_CORRELATION,
                study_type=StudyType.IN_VITRO_CELLULAR,
                confidence_score=0.5,
                data_origin=DataOrigin.LITERATURE_RETRIEVAL,
                source_database="PubMed",
                extracted_statement="Mentioned in review",
                citation=sample_citation,
            )
        ]
        score = scoring_engine.calculate_genetic_evidence_score(non_genetic)
        assert score == 0.0

    def test_tractability_scoring_clinical_precedence(self, scoring_engine, sample_druggability_profile):
        score = scoring_engine.calculate_tractability_score(sample_druggability_profile)
        # Antibody clinical precedence boosts to at least 80.0
        assert score >= 80.0

    def test_tractability_unassessed_default(self, scoring_engine):
        score = scoring_engine.calculate_tractability_score(None)
        assert score == 25.0

    def test_literature_scoring_log_scaling(self, scoring_engine, sample_citation):
        # 1 paper
        single_paper_item = [
            EvidenceItem(
                evidence_id="EV-1",
                target_symbol="APP",
                disease_name="Alzheimer's",
                evidence_type=EvidenceType.LITERATURE_COOCCURRENCE,
                causality_level=CausalityLevel.FUNCTIONAL_ASSOCIATION,
                study_type=StudyType.IN_VITRO_CELLULAR,
                confidence_score=0.8,
                data_origin=DataOrigin.LITERATURE_RETRIEVAL,
                source_database="PubMed",
                extracted_statement="Statement",
                citation=sample_citation,
            )
        ]
        score_single = scoring_engine.calculate_literature_score(single_paper_item)
        assert score_single > 0.0

        # Many papers (create 30 mock items with different PMIDs)
        many_items = []
        for i in range(30):
            cit = CitationReference(pmid=f"1000{i:03d}", title=f"Paper {i}")
            many_items.append(
                EvidenceItem(
                    evidence_id=f"EV-MANY-{i}",
                    target_symbol="APP",
                    disease_name="Alzheimer's",
                    evidence_type=EvidenceType.LITERATURE_COOCCURRENCE,
                    causality_level=CausalityLevel.FUNCTIONAL_ASSOCIATION,
                    study_type=StudyType.IN_VITRO_CELLULAR,
                    confidence_score=0.8,
                    data_origin=DataOrigin.LITERATURE_RETRIEVAL,
                    source_database="PubMed",
                    extracted_statement=f"Statement {i}",
                    citation=cit,
                )
            )
        score_many = scoring_engine.calculate_literature_score(many_items)
        assert score_many > score_single
        assert score_many >= 70.0

    def test_experimental_validation_scoring(self, scoring_engine, sample_experimental_records):
        score = scoring_engine.calculate_experimental_validation_score(sample_experimental_records)
        # Has CRISPR (35) + sig (15) + coverage (5) -> 55.0
        assert score >= 50.0

    def test_experimental_validation_zero_when_none(self, scoring_engine):
        score = scoring_engine.calculate_experimental_validation_score([])
        assert score == 0.0

    def test_safety_score_penalizes_concerns(self, scoring_engine, sample_druggability_profile):
        score_clean = scoring_engine.calculate_safety_score(sample_druggability_profile, [])
        assert score_clean == 80.0

        profile_with_tox = DruggabilityProfile(
            target_symbol="TOX_TARGET",
            overall_tractability_score=50.0,
            safety_concerns=["Hepatotoxicity risk", "QTc prolongation liability"],
        )
        score_tox = scoring_engine.calculate_safety_score(profile_with_tox, [])
        assert score_tox == 80.0 - (2 * 15.0)  # 50.0

    def test_contradiction_penalty(self, scoring_engine, sample_citation):
        clean_items = [
            EvidenceItem(
                evidence_id="EV-C1",
                target_symbol="T1",
                disease_name="D1",
                evidence_type=EvidenceType.GENETIC_ASSOCIATION,
                causality_level=CausalityLevel.FUNCTIONAL_ASSOCIATION,
                study_type=StudyType.HUMAN_GWAS,
                confidence_score=0.8,
                is_contradictory=False,
                data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
                source_database="PubMed",
                extracted_statement="Positive finding",
                citation=sample_citation,
            )
        ]
        assert scoring_engine.calculate_contradiction_penalty(clean_items) == 0.0

        contradictory_items = clean_items + [
            EvidenceItem(
                evidence_id="EV-C2",
                target_symbol="T1",
                disease_name="D1",
                evidence_type=EvidenceType.GENETIC_ASSOCIATION,
                causality_level=CausalityLevel.CONTRADICTORY_EVIDENCE,
                study_type=StudyType.HUMAN_GWAS,
                confidence_score=0.8,
                is_contradictory=True,
                data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
                source_database="PubMed",
                extracted_statement="Contradicting finding in independent cohort",
                citation=sample_citation,
            )
        ]
        penalty = scoring_engine.calculate_contradiction_penalty(contradictory_items)
        assert penalty >= 15.0

    def test_rank_target_deterministic_and_bounded(
        self,
        scoring_engine,
        sample_target_candidate,
        sample_evidence_items,
        sample_druggability_profile,
        sample_experimental_records,
    ):
        ranked = scoring_engine.rank_target(
            target=sample_target_candidate,
            evidence_items=sample_evidence_items,
            druggability_profile=sample_druggability_profile,
            experimental_records=sample_experimental_records,
            open_targets_overall_score=0.88,
        )

        assert ranked.target_symbol == "TREM2"
        assert 0.0 <= ranked.overall_priority_score <= 100.0
        assert ranked.confidence_tier in (ConfidenceTier.HIGH, ConfidenceTier.MEDIUM, ConfidenceTier.LOW)
        assert 0.0 <= ranked.confidence_score <= 1.0

        # Verify all sub-score components are populated
        bd = ranked.score_breakdown
        assert bd.disease_association_score == 88.0
        assert bd.genetic_evidence_score > 0
        assert bd.target_tractability_score > 0
        assert bd.literature_evidence_score > 0
        assert bd.experimental_validation_score > 0
        assert bd.safety_profile_score > 0
        assert bd.final_clamped_score == ranked.overall_priority_score

        # Verify radar data
        assert len(ranked.radar_data) == 6
        assert "Disease Association" in ranked.radar_data
        assert "Genetic Rigor" in ranked.radar_data

        # Verify explainability
        assert len(ranked.strengths) > 0
        assert len(ranked.key_pmids) > 0
