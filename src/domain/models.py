from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple, Any
from pydantic import BaseModel, Field, field_validator

from src.domain.enums import (
    EvidenceType,
    CausalityLevel,
    StudyType,
    TractabilityModality,
    TractabilityBucket,
    DataOrigin,
    DirectionOfEffect,
    WorkflowStage,
    ConfidenceTier,
)


class ProvenanceRecord(BaseModel):
    """Metadata tracking the exact origin and execution trace of any record."""
    source_database: str
    source_url_or_endpoint: Optional[str] = None
    query_or_input: Optional[str] = None
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tool_name: Optional[str] = None
    data_origin: DataOrigin
    checksum_or_id: Optional[str] = None
    curator_or_agent: str = "system"


class CitationReference(BaseModel):
    """Bibliographic citation supporting a scientific fact or evidence item."""
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    doi: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    journal: Optional[str] = None
    publication_year: Optional[int] = None
    url: Optional[str] = None

    @property
    def formatted_citation(self) -> str:
        first_author = self.authors[0] if self.authors else "Unknown"
        et_al = " et al." if len(self.authors) > 1 else ""
        year_str = f" ({self.publication_year})" if self.publication_year else ""
        pmid_str = f" [PMID: {self.pmid}]" if self.pmid else ""
        return f"{first_author}{et_al}{year_str}. {self.title}{pmid_str}"


class PubMedArticle(BaseModel):
    """Structured literature document retrieved from NCBI PubMed/PMC."""
    pmid: str
    pmcid: Optional[str] = None
    doi: Optional[str] = None
    title: str
    abstract: str
    authors: List[str] = Field(default_factory=list)
    journal: Optional[str] = None
    publication_year: Optional[int] = None
    mesh_terms: List[str] = Field(default_factory=list)
    citation: Optional[CitationReference] = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_origin: DataOrigin = DataOrigin.LITERATURE_RETRIEVAL


class EvidenceItem(BaseModel):
    """
    Atomic unit of biomedical evidence linking a candidate target to a disease.
    Strictly preserves source provenance, study rigor, and causality classification.
    """
    evidence_id: str
    target_symbol: str
    target_ensembl_id: Optional[str] = None
    disease_name: str
    disease_efo_id: Optional[str] = None
    evidence_type: EvidenceType
    causality_level: CausalityLevel
    study_type: StudyType
    sample_size: Optional[int] = None
    p_value: Optional[float] = None
    effect_size: Optional[float] = None
    direction: DirectionOfEffect = DirectionOfEffect.UNKNOWN
    confidence_score: float = Field(ge=0.0, le=1.0)
    is_contradictory: bool = False
    data_origin: DataOrigin
    source_database: str
    citation: Optional[CitationReference] = None
    extracted_statement: str
    curation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("confidence_score")
    @classmethod
    def check_confidence_bounds(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("confidence_score must be between 0.0 and 1.0")
        return round(v, 4)


class DruggabilityModalityDetail(BaseModel):
    """Detailed tractability breakdown for a specific therapeutic modality."""
    modality: TractabilityModality
    bucket: TractabilityBucket
    score: float = Field(ge=0.0, le=100.0)
    details: str
    pdb_structures: List[str] = Field(default_factory=list)
    clinical_phase: Optional[int] = Field(default=None, ge=0, le=4)


class DruggabilityProfile(BaseModel):
    """Comprehensive druggability and tractability assessment for a candidate target."""
    target_symbol: str
    modalities: Dict[TractabilityModality, DruggabilityModalityDetail] = Field(default_factory=dict)
    overall_tractability_score: float = Field(ge=0.0, le=100.0)
    has_small_molecule_binder: bool = False
    has_approved_drug: bool = False
    safety_concerns: List[str] = Field(default_factory=list)
    data_origin: DataOrigin = DataOrigin.EXPERIMENTALLY_MEASURED
    summary_rationale: str = ""


class ExperimentalRecord(BaseModel):
    """
    Internal laboratory assay record (e.g. CRISPR KO, RNA-seq, SPR binding).
    Demonstrates ingestion architecture while strictly labeling synthetic demonstration data.
    """
    record_id: str
    dataset_id: str
    target_symbol: str
    cell_line_or_model: str
    assay_type: str
    measurement_name: str
    measurement_value: float
    measurement_unit: str
    p_value: Optional[float] = None
    replicates: int = Field(default=3, ge=1)
    qc_passed: bool = True
    data_origin: DataOrigin = DataOrigin.SYNTHETIC_DEMONSTRATION
    synthetic_disclaimer: str = "Synthetic demonstration dataset — not proprietary experimental data."
    notes: Optional[str] = None


class DatasetMetadata(BaseModel):
    """Metadata and provenance for an ingested experimental dataset."""
    dataset_id: str
    dataset_name: str
    is_synthetic: bool = True
    disclaimer: str = "Synthetic demonstration dataset — not proprietary experimental data."
    version: str = "1.0.0"
    platform: str
    organism: str = "Homo sapiens"
    record_count: int = 0
    provenance: Optional[ProvenanceRecord] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TargetCandidate(BaseModel):
    """Candidate therapeutic target identified from literature or biological databases."""
    target_symbol: str
    target_name: Optional[str] = None
    ensembl_id: Optional[str] = None
    uniprot_id: Optional[str] = None
    disease_name: str
    disease_efo_id: Optional[str] = None
    identification_sources: List[str] = Field(default_factory=list)
    initial_rationale: str = ""


class ScoreBreakdown(BaseModel):
    """
    Transparent mathematical component breakdown of the deterministic target ranking score.
    No black-box or fabricated LLM numbers allowed.
    """
    disease_association_score: float = Field(ge=0.0, le=100.0)
    genetic_evidence_score: float = Field(ge=0.0, le=100.0)
    target_tractability_score: float = Field(ge=0.0, le=100.0)
    literature_evidence_score: float = Field(ge=0.0, le=100.0)
    experimental_validation_score: float = Field(ge=0.0, le=100.0)
    safety_profile_score: float = Field(ge=0.0, le=100.0)
    contradiction_penalty: float = Field(ge=0.0)
    weights_applied: Dict[str, float] = Field(default_factory=dict)
    raw_composite_score: float
    final_clamped_score: float = Field(ge=0.0, le=100.0)


class RankedTarget(BaseModel):
    """Fully evaluated and ranked target with explainable scoring and evidence traceability."""
    target_symbol: str
    target_name: Optional[str] = None
    disease_name: str
    overall_priority_score: float = Field(ge=0.0, le=100.0)
    confidence_tier: ConfidenceTier
    confidence_score: float = Field(ge=0.0, le=1.0)
    score_breakdown: ScoreBreakdown
    evidence_count: int
    key_pmids: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    experimental_validation_status: str
    tractability_summary: str
    radar_data: Dict[str, float] = Field(default_factory=dict)


class CompoundBioactivity(BaseModel):
    """Empirically measured chemical bioactivity queried from ChEMBL."""
    compound_id: str
    compound_name: Optional[str] = None
    smiles: Optional[str] = None
    target_symbol: str
    activity_type: str  # e.g., "IC50", "Ki", "EC50"
    activity_value: float
    activity_unit: str  # e.g., "nM"
    assay_chembl_id: Optional[str] = None
    data_origin: DataOrigin = DataOrigin.EXPERIMENTALLY_MEASURED


class ScreeningPrediction(BaseModel):
    """
    Computationally predicted compound screening/docking score.
    Clearly distinguishes in silico predictions from experimental measurements.
    """
    compound_id: str
    smiles: str
    target_symbol: str
    prediction_method: str
    predicted_binding_affinity_kcal_mol: Optional[float] = None
    predicted_kd_nm: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    molecular_weight: Optional[float] = None
    logp: Optional[float] = None
    tpsa: Optional[float] = None
    data_origin: DataOrigin = DataOrigin.COMPUTATIONAL_PREDICTION
    disclaimer: str = "Computational simulation prediction — not experimentally measured."


class AgentTraceEvent(BaseModel):
    """Audit log event recording multi-agent execution steps."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    agent_name: str
    stage: WorkflowStage
    input_summary: str
    output_summary: str
    tool_calls: List[str] = Field(default_factory=list)
    duration_ms: float = 0.0
    status: str = "success"
    notes: Optional[str] = None


class ResearchReport(BaseModel):
    """Final comprehensive scientific report artifact."""
    report_id: str
    session_id: str
    disease_name: str
    research_question: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executive_summary: str
    top_targets: List[RankedTarget] = Field(default_factory=list)
    methodology: str
    all_citations: List[CitationReference] = Field(default_factory=list)
    limitations_disclaimer: str = (
        "This report is generated by an AI research platform for hypothesis generation and "
        "target prioritization only. It does NOT constitute medical advice, clinical recommendation, "
        "or validated drug discovery. All candidate targets require empirical wet-lab validation."
    )
    synthetic_data_note: str = (
        "Any internal experimental datasets utilized are synthetic demonstration records "
        "and do NOT represent proprietary company data."
    )
