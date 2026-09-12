import sys
from pathlib import Path
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.enums import (
    EvidenceType,
    CausalityLevel,
    StudyType,
    TractabilityModality,
    TractabilityBucket,
    DataOrigin,
    DirectionOfEffect,
)
from src.domain.models import (
    CitationReference,
    EvidenceItem,
    TargetCandidate,
    DruggabilityModalityDetail,
    DruggabilityProfile,
    ExperimentalRecord,
)
from src.engine.scoring import TargetScoringEngine
from src.engine.experimental_loader import ExperimentalDatasetLoader


@pytest.fixture
def sample_citation():
    return CitationReference(
        pmid="31234567",
        doi="10.1038/s41586-019-1234-5",
        title="Microglial TREM2 orchestrates amyloid clearance in Alzheimer models",
        authors=["Smith J", "Doe A", "Johnson K"],
        journal="Nature",
        publication_year=2021,
        url="https://pubmed.ncbi.nlm.nih.gov/31234567/",
    )


@pytest.fixture
def sample_evidence_items(sample_citation):
    return [
        EvidenceItem(
            evidence_id="EVID-001",
            target_symbol="TREM2",
            target_ensembl_id="ENSG00000095977",
            disease_name="Alzheimer's disease",
            disease_efo_id="EFO_0000249",
            evidence_type=EvidenceType.GENETIC_ASSOCIATION,
            causality_level=CausalityLevel.CAUSAL_DEMONSTRATED,
            study_type=StudyType.HUMAN_GWAS,
            sample_size=45000,
            p_value=2.4e-12,
            confidence_score=0.95,
            is_contradictory=False,
            data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
            source_database="OpenTargets",
            citation=sample_citation,
            extracted_statement="Rare R47H variant in TREM2 increases Alzheimer's risk by 3-fold.",
        ),
        EvidenceItem(
            evidence_id="EVID-002",
            target_symbol="TREM2",
            target_ensembl_id="ENSG00000095977",
            disease_name="Alzheimer's disease",
            disease_efo_id="EFO_0000249",
            evidence_type=EvidenceType.LITERATURE_COOCCURRENCE,
            causality_level=CausalityLevel.FUNCTIONAL_ASSOCIATION,
            study_type=StudyType.IN_VITRO_CELLULAR,
            confidence_score=0.85,
            is_contradictory=False,
            data_origin=DataOrigin.LITERATURE_RETRIEVAL,
            source_database="PubMed",
            citation=sample_citation,
            extracted_statement="Activation of TREM2 promotes microglial survival and amyloid beta uptake.",
        ),
    ]


@pytest.fixture
def sample_druggability_profile():
    return DruggabilityProfile(
        target_symbol="TREM2",
        modalities={
            TractabilityModality.ANTIBODY: DruggabilityModalityDetail(
                modality=TractabilityModality.ANTIBODY,
                bucket=TractabilityBucket.CLINICAL_PRECEDENCE,
                score=90.0,
                details="Agonist monoclonal antibodies in Phase II clinical trials (AL002).",
                clinical_phase=2,
            ),
            TractabilityModality.SMALL_MOLECULE: DruggabilityModalityDetail(
                modality=TractabilityModality.SMALL_MOLECULE,
                bucket=TractabilityBucket.DISCOVERY_PRECEDENCE,
                score=65.0,
                details="Extracellular Ig-like V-type domain possesses shallow hydrophobic groove.",
                pdb_structures=["5ELI", "6DRX"],
            ),
        },
        overall_tractability_score=85.0,
        has_small_molecule_binder=True,
        has_approved_drug=False,
        safety_concerns=[],
        summary_rationale="High biologic tractability with Phase II clinical precedent.",
    )


@pytest.fixture
def sample_experimental_records():
    return [
        ExperimentalRecord(
            record_id="REC-TEST-001",
            dataset_id="SYNTH-ASSAY-2026-001",
            target_symbol="TREM2",
            cell_line_or_model="iPSC-derived microglia",
            assay_type="CRISPR_KO_Phagocytosis",
            measurement_name="amyloid_phagocytosis_rescue_pct",
            measurement_value=48.5,
            measurement_unit="%",
            p_value=0.0012,
            replicates=4,
            qc_passed=True,
            data_origin=DataOrigin.SYNTHETIC_DEMONSTRATION,
            synthetic_disclaimer="Synthetic demonstration dataset — not proprietary experimental data.",
        )
    ]


@pytest.fixture
def sample_target_candidate():
    return TargetCandidate(
        target_symbol="TREM2",
        target_name="Triggering Receptor Expressed On Myeloid Cells 2",
        ensembl_id="ENSG00000095977",
        uniprot_id="Q9NZC2",
        disease_name="Alzheimer's disease",
        disease_efo_id="EFO_0000249",
        identification_sources=["Literature", "OpenTargets"],
        initial_rationale="Key innate immune receptor regulating neuroinflammation.",
    )


@pytest.fixture
def scoring_engine():
    return TargetScoringEngine()


@pytest.fixture
def synthetic_data_path():
    return PROJECT_ROOT / "data" / "synthetic_experimental" / "sample_target_validation_assays.json"
