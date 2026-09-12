import pytest
from pydantic import ValidationError

from src.domain.enums import (
    EvidenceType,
    CausalityLevel,
    StudyType,
    TractabilityModality,
    TractabilityBucket,
    DataOrigin,
    ConfidenceTier,
)
from src.domain.models import (
    CitationReference,
    PubMedArticle,
    EvidenceItem,
    DruggabilityProfile,
    DruggabilityModalityDetail,
    ExperimentalRecord,
    RankedTarget,
    ScoreBreakdown,
    CompoundBioactivity,
    ScreeningPrediction,
)


class TestDomainModels:

    def test_citation_reference_formatting(self):
        cit = CitationReference(
            pmid="12345678",
            title="Amyloid cascade hypothesis in Alzheimer's",
            authors=["Hardy J", "Higgins G"],
            journal="Science",
            publication_year=1992,
        )
        assert "Hardy J et al." in cit.formatted_citation
        assert "(1992)" in cit.formatted_citation
        assert "[PMID: 12345678]" in cit.formatted_citation

    def test_citation_reference_single_author(self):
        cit = CitationReference(
            pmid="87654321",
            title="Single author review",
            authors=["Solo A"],
            publication_year=2020,
        )
        assert "Solo A" in cit.formatted_citation
        assert "et al." not in cit.formatted_citation

    def test_evidence_item_valid(self, sample_citation):
        item = EvidenceItem(
            evidence_id="EV-001",
            target_symbol="APP",
            disease_name="Alzheimer's",
            evidence_type=EvidenceType.GENETIC_ASSOCIATION,
            causality_level=CausalityLevel.CAUSAL_DEMONSTRATED,
            study_type=StudyType.HUMAN_GWAS,
            confidence_score=0.92,
            data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
            source_database="OpenTargets",
            extracted_statement="APP Swedish mutation causes early-onset Alzheimer's.",
            citation=sample_citation,
        )
        assert item.target_symbol == "APP"
        assert item.confidence_score == 0.92
        assert not item.is_contradictory

    def test_evidence_item_confidence_bounds_enforced(self):
        with pytest.raises(ValidationError):
            EvidenceItem(
                evidence_id="EV-INVALID",
                target_symbol="APP",
                disease_name="Alzheimer's",
                evidence_type=EvidenceType.GENETIC_ASSOCIATION,
                causality_level=CausalityLevel.CAUSAL_DEMONSTRATED,
                study_type=StudyType.HUMAN_GWAS,
                confidence_score=1.5,  # Exceeds 1.0 bound
                data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
                source_database="OpenTargets",
                extracted_statement="Statement",
            )

    def test_experimental_record_synthetic_label_enforced(self):
        rec = ExperimentalRecord(
            record_id="REC-01",
            dataset_id="DS-01",
            target_symbol="PSEN1",
            cell_line_or_model="HEK293",
            assay_type="Binding",
            measurement_name="Kd",
            measurement_value=12.5,
            measurement_unit="nM",
            replicates=3,
        )
        assert rec.data_origin == DataOrigin.SYNTHETIC_DEMONSTRATION
        assert "Synthetic demonstration dataset" in rec.synthetic_disclaimer

    def test_experimental_record_negative_replicates_rejected(self):
        with pytest.raises(ValidationError):
            ExperimentalRecord(
                record_id="REC-02",
                dataset_id="DS-01",
                target_symbol="PSEN1",
                cell_line_or_model="HEK293",
                assay_type="Binding",
                measurement_name="Kd",
                measurement_value=12.5,
                measurement_unit="nM",
                replicates=0,  # Must be >= 1
            )

    def test_compound_bioactivity_origin(self):
        bio = CompoundBioactivity(
            compound_id="CHEMBL123",
            target_symbol="BACE1",
            activity_type="IC50",
            activity_value=15.0,
            activity_unit="nM",
        )
        assert bio.data_origin == DataOrigin.EXPERIMENTALLY_MEASURED

    def test_screening_prediction_disclaimer_present(self):
        pred = ScreeningPrediction(
            compound_id="CMPD-001",
            smiles="CC(=O)Oc1ccccc1C(=O)O",
            target_symbol="PTGS2",
            prediction_method="PhysicoChemicalHeuristic",
            predicted_binding_affinity_kcal_mol=-6.8,
        )
        assert pred.data_origin == DataOrigin.COMPUTATIONAL_PREDICTION
        assert "not experimentally measured" in pred.disclaimer.lower()
