from enum import Enum


class EvidenceType(str, Enum):
    """Classification of scientific evidence sources and modalities."""
    GENETIC_ASSOCIATION = "genetic_association"
    SOMATIC_MUTATION = "somatic_mutation"
    LITERATURE_COOCCURRENCE = "literature_cooccurrence"
    PATHWAY_PERTURBATION = "pathway_perturbation"
    RNA_EXPRESSION = "rna_expression"
    ANIMAL_MODEL = "animal_model"
    INTERNAL_EXPERIMENT = "internal_experiment"
    CLINICAL_TRIAL = "clinical_trial"


class CausalityLevel(str, Enum):
    """Categorization of evidence strength regarding causal link to disease."""
    CAUSAL_DEMONSTRATED = "causal_demonstrated"          # e.g., Mendelian or validated loss-of-function mutation
    FUNCTIONAL_ASSOCIATION = "functional_association"    # e.g., CRISPR knockout rescues disease phenotype
    STATISTICAL_CORRELATION = "statistical_correlation"  # e.g., observational or expression profiling correlation
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"    # e.g., conflicting findings across independent cohorts


class StudyType(str, Enum):
    """Experimental or analytical methodology used in the study."""
    HUMAN_CLINICAL = "human_clinical"
    HUMAN_GWAS = "human_gwas"
    IN_VIVO_ANIMAL = "in_vivo_animal"
    IN_VITRO_CELLULAR = "in_vitro_cellular"
    COMPUTATIONAL_PREDICTION = "computational_prediction"


class TractabilityModality(str, Enum):
    """Therapeutic modalities assessed for target druggability."""
    SMALL_MOLECULE = "small_molecule"
    ANTIBODY = "antibody"
    PROTAC = "protac"
    OTHER_MODALITY = "other_modality"


class TractabilityBucket(str, Enum):
    """Open Targets tractability buckets representing druggability precedence."""
    CLINICAL_PRECEDENCE = "clinical_precedence"      # Approved drug or clinical trial candidate
    DISCOVERY_PRECEDENCE = "discovery_precedence"    # High-quality tool compound / bioactivity data
    PREDICTED_TRACTABLE = "predicted_tractable"      # Druggable pocket or accessible epitope predicted
    UNKNOWN = "unknown"


class DataOrigin(str, Enum):
    """
    Crucial ontological distinction between empirical data, simulations,
    synthetic demo datasets, and agent interpretations.
    Never confuse agent inferences or simulations with verified empirical facts.
    """
    EXPERIMENTALLY_MEASURED = "experimentally_measured"
    SYNTHETIC_DEMONSTRATION = "synthetic_demonstration"
    COMPUTATIONAL_PREDICTION = "computational_prediction"
    AGENT_INTERPRETATION = "agent_interpretation"
    LITERATURE_RETRIEVAL = "literature_retrieval"


class DirectionOfEffect(str, Enum):
    """Directionality of perturbation or expression in disease state."""
    RISK_INCREASING = "risk_increasing"
    PROTECTIVE = "protective"
    UPREGULATED = "upregulated"
    DOWNREGULATED = "downregulated"
    NEUTRAL = "neutral"
    CONTRADICTORY = "contradictory"
    UNKNOWN = "unknown"


class WorkflowStage(str, Enum):
    """Stages of the LangGraph multi-agent drug discovery pipeline."""
    INITIALIZATION = "initialization"
    LITERATURE_SEARCH = "literature_search"
    TARGET_IDENTIFICATION = "target_identification"
    EVIDENCE_EVALUATION = "evidence_evaluation"
    TRACTABILITY_ASSESSMENT = "tractability_assessment"
    EXPERIMENTAL_MATCHING = "experimental_matching"
    TARGET_RANKING = "target_ranking"
    COMPOUND_SCREENING = "compound_screening"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfidenceTier(str, Enum):
    """Confidence tier for target prioritization."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCONFIRMED = "unconfirmed"
