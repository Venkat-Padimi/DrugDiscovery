import math
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel

from src.domain.enums import (
    ConfidenceTier,
    EvidenceType,
    CausalityLevel,
    StudyType,
    TractabilityModality,
    TractabilityBucket,
)
from src.domain.models import (
    EvidenceItem,
    DruggabilityProfile,
    ExperimentalRecord,
    ScoreBreakdown,
    RankedTarget,
    TargetCandidate,
)
from config.settings import ScoringWeights, settings


class TargetScoringEngine:
    """
    Deterministic scoring and prioritization engine for therapeutic targets.
    
    CRITICAL SCIENTIFIC SAFETY RULE:
    Calculates transparent, reproducible composite scores from structured evidence.
    No arbitrary black-box scores or hallucinated LLM numbers are allowed.
    """

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or settings.scoring_weights

    def calculate_disease_association_score(
        self,
        evidence_items: List[EvidenceItem],
        open_targets_overall_score: Optional[float] = None,
    ) -> float:
        """
        Calculates S_disease (0-100) based on Open Targets association score
        and curated disease association evidence.
        """
        if open_targets_overall_score is not None:
            base_score = min(100.0, max(0.0, open_targets_overall_score * 100.0))
        else:
            # Derive from evidence items if direct Open Targets score is absent
            assoc_items = [
                item for item in evidence_items
                if item.evidence_type in (
                    EvidenceType.GENETIC_ASSOCIATION,
                    EvidenceType.CLINICAL_TRIAL,
                    EvidenceType.PATHWAY_PERTURBATION,
                )
            ]
            if not assoc_items:
                return 10.0  # minimal baseline for candidate nomination
            max_conf = max(item.confidence_score for item in assoc_items)
            base_score = max_conf * 80.0

        return round(min(100.0, max(0.0, base_score)), 2)

    def calculate_genetic_evidence_score(self, evidence_items: List[EvidenceItem]) -> float:
        """
        Calculates S_genetic (0-100). Genetic evidence significantly de-risks
        drug targets in clinical development.
        """
        genetic_items = [
            item for item in evidence_items
            if item.evidence_type in (EvidenceType.GENETIC_ASSOCIATION, EvidenceType.SOMATIC_MUTATION)
            or item.study_type == StudyType.HUMAN_GWAS
        ]
        if not genetic_items:
            return 0.0

        score = 0.0
        has_causal = any(i.causality_level == CausalityLevel.CAUSAL_DEMONSTRATED for i in genetic_items)
        has_functional = any(i.causality_level == CausalityLevel.FUNCTIONAL_ASSOCIATION for i in genetic_items)
        has_gwas_sig = any(i.p_value is not None and i.p_value < 5e-8 for i in genetic_items)

        if has_causal:
            score += 60.0
        elif has_functional:
            score += 40.0
        else:
            score += 20.0

        if has_gwas_sig:
            score += 25.0

        # Scale by highest confidence score
        max_conf = max(i.confidence_score for i in genetic_items)
        score += max_conf * 15.0

        return round(min(100.0, max(0.0, score)), 2)

    def calculate_tractability_score(
        self, druggability_profile: Optional[DruggabilityProfile]
    ) -> float:
        """
        Calculates S_tractability (0-100) based on Open Targets tractability buckets
        and structural / ligand feasibility.
        """
        if not druggability_profile:
            return 25.0  # default unassessed baseline

        score = druggability_profile.overall_tractability_score
        # Check specific modalities
        sm_detail = druggability_profile.modalities.get(TractabilityModality.SMALL_MOLECULE)
        if sm_detail:
            if sm_detail.bucket == TractabilityBucket.CLINICAL_PRECEDENCE:
                score = max(score, 95.0)
            elif sm_detail.bucket == TractabilityBucket.DISCOVERY_PRECEDENCE:
                score = max(score, 75.0)
            elif sm_detail.bucket == TractabilityBucket.PREDICTED_TRACTABLE:
                score = max(score, 55.0)

        ab_detail = druggability_profile.modalities.get(TractabilityModality.ANTIBODY)
        if ab_detail and ab_detail.bucket in (TractabilityBucket.CLINICAL_PRECEDENCE, TractabilityBucket.DISCOVERY_PRECEDENCE):
            score = max(score, 80.0)

        return round(min(100.0, max(0.0, score)), 2)

    def calculate_literature_score(self, evidence_items: List[EvidenceItem]) -> float:
        """
        Calculates S_literature (0-100) using log-scaled independent PMID counts.
        Formula: 100 * min(1.0, log10(N + 1) / log10(51))
        50+ distinct publications reaches 100%.
        """
        unique_pmids = set(
            item.citation.pmid for item in evidence_items
            if item.citation and item.citation.pmid
        )
        n = len(unique_pmids)
        if n == 0:
            # Fallback to evidence count if PMIDs are unparsed
            n = len([i for i in evidence_items if i.evidence_type == EvidenceType.LITERATURE_COOCCURRENCE])

        if n == 0:
            return 5.0

        log_factor = math.log10(n + 1) / math.log10(51)
        score = min(1.0, log_factor) * 90.0

        # Clinical trial bonus
        has_clinical = any(i.study_type == StudyType.HUMAN_CLINICAL for i in evidence_items)
        if has_clinical:
            score += 10.0

        return round(min(100.0, max(0.0, score)), 2)

    def calculate_experimental_validation_score(
        self,
        experimental_records: List[ExperimentalRecord],
    ) -> float:
        """
        Calculates S_experimental (0-100) based on internal or proprietary assay records.
        """
        if not experimental_records:
            return 0.0

        qc_passed_records = [r for r in experimental_records if r.qc_passed]
        if not qc_passed_records:
            return 10.0

        score = 0.0
        # Replicates and statistical significance
        has_sig = any(r.p_value is not None and r.p_value < 0.05 for r in qc_passed_records)
        has_crispr = any("crispr" in r.assay_type.lower() for r in qc_passed_records)
        has_rnaseq = any("rna" in r.assay_type.lower() or "expression" in r.assay_type.lower() for r in qc_passed_records)
        has_binding = any("spr" in r.assay_type.lower() or "binding" in r.assay_type.lower() for r in qc_passed_records)

        if has_crispr:
            score += 35.0
        if has_rnaseq:
            score += 25.0
        if has_binding:
            score += 25.0
        if has_sig:
            score += 15.0

        # Scale by count of passed assays (up to 3)
        coverage_bonus = min(15.0, len(qc_passed_records) * 5.0)
        score += coverage_bonus

        return round(min(100.0, max(0.0, score)), 2)

    def calculate_safety_score(
        self,
        druggability_profile: Optional[DruggabilityProfile],
        evidence_items: List[EvidenceItem],
    ) -> float:
        """
        Calculates S_safety (0-100). Higher score indicates safer / lower off-target risk.
        Baseline is 80.0, reduced for flagged safety liabilities.
        """
        base_safety = 80.0
        if druggability_profile and druggability_profile.safety_concerns:
            # Deduct 15 points per distinct safety concern
            penalty = len(druggability_profile.safety_concerns) * 15.0
            base_safety = max(20.0, base_safety - penalty)

        return round(min(100.0, max(0.0, base_safety)), 2)

    def calculate_contradiction_penalty(self, evidence_items: List[EvidenceItem]) -> float:
        """
        Calculates penalty deduction if scientific literature or assays present conflicting results.
        """
        contradictory_items = [
            i for i in evidence_items
            if i.is_contradictory or i.causality_level == CausalityLevel.CONTRADICTORY_EVIDENCE
        ]
        if not contradictory_items:
            return 0.0

        ratio = len(contradictory_items) / max(1, len(evidence_items))
        penalty = self.weights.contradiction_penalty_min + (
            (self.weights.contradiction_penalty_max - self.weights.contradiction_penalty_min) * ratio
        )
        return round(min(self.weights.contradiction_penalty_max, penalty), 2)

    def compute_confidence(
        self,
        evidence_items: List[EvidenceItem],
        has_experimental: bool,
        has_druggability: bool,
    ) -> Tuple[float, ConfidenceTier]:
        """
        Determines overall confidence score (0.0 to 1.0) and tier based on evidence volume,
        study rigor, and absence of severe contradictions.
        """
        if not evidence_items:
            return 0.1, ConfidenceTier.LOW

        completeness_dimensions = 0
        if any(i.evidence_type == EvidenceType.GENETIC_ASSOCIATION for i in evidence_items):
            completeness_dimensions += 1
        if any(i.evidence_type == EvidenceType.LITERATURE_COOCCURRENCE for i in evidence_items):
            completeness_dimensions += 1
        if has_experimental:
            completeness_dimensions += 1
        if has_druggability:
            completeness_dimensions += 1

        dimension_score = completeness_dimensions / 4.0

        contradiction_count = sum(1 for i in evidence_items if i.is_contradictory)
        concordance_ratio = 1.0 - (contradiction_count / max(1, len(evidence_items)))

        avg_evidence_confidence = sum(i.confidence_score for i in evidence_items) / max(1, len(evidence_items))

        confidence_score = round(
            0.4 * dimension_score + 0.3 * concordance_ratio + 0.3 * avg_evidence_confidence,
            2,
        )

        if confidence_score >= 0.70 and len(evidence_items) >= 3:
            tier = ConfidenceTier.HIGH
        elif confidence_score >= 0.40:
            tier = ConfidenceTier.MEDIUM
        else:
            tier = ConfidenceTier.LOW

        return confidence_score, tier

    def rank_target(
        self,
        target: TargetCandidate,
        evidence_items: List[EvidenceItem],
        druggability_profile: Optional[DruggabilityProfile] = None,
        experimental_records: Optional[List[ExperimentalRecord]] = None,
        open_targets_overall_score: Optional[float] = None,
    ) -> RankedTarget:
        """
        Executes full deterministic scoring for a candidate target.
        """
        records = experimental_records or []
        s_disease = self.calculate_disease_association_score(evidence_items, open_targets_overall_score)
        s_genetic = self.calculate_genetic_evidence_score(evidence_items)
        s_tractability = self.calculate_tractability_score(druggability_profile)
        s_literature = self.calculate_literature_score(evidence_items)
        s_experimental = self.calculate_experimental_validation_score(records)
        s_safety = self.calculate_safety_score(druggability_profile, evidence_items)
        contradiction_penalty = self.calculate_contradiction_penalty(evidence_items)

        weights_dict = {
            "disease_association": self.weights.disease_association,
            "genetic_evidence": self.weights.genetic_evidence,
            "target_tractability": self.weights.target_tractability,
            "literature_evidence": self.weights.literature_evidence,
            "experimental_validation": self.weights.experimental_validation,
            "safety_profile": self.weights.safety_profile,
        }

        raw_composite = (
            self.weights.disease_association * s_disease
            + self.weights.genetic_evidence * s_genetic
            + self.weights.target_tractability * s_tractability
            + self.weights.literature_evidence * s_literature
            + self.weights.experimental_validation * s_experimental
            + self.weights.safety_profile * s_safety
            - contradiction_penalty
        )

        final_clamped = round(min(100.0, max(0.0, raw_composite)), 2)

        breakdown = ScoreBreakdown(
            disease_association_score=s_disease,
            genetic_evidence_score=s_genetic,
            target_tractability_score=s_tractability,
            literature_evidence_score=s_literature,
            experimental_validation_score=s_experimental,
            safety_profile_score=s_safety,
            contradiction_penalty=contradiction_penalty,
            weights_applied=weights_dict,
            raw_composite_score=round(raw_composite, 2),
            final_clamped_score=final_clamped,
        )

        conf_score, conf_tier = self.compute_confidence(
            evidence_items=evidence_items,
            has_experimental=bool(records),
            has_druggability=druggability_profile is not None,
        )

        # Extract unique PMIDs
        pmids = sorted(list(set(
            i.citation.pmid for i in evidence_items
            if i.citation and i.citation.pmid
        )))

        # Derive explainable strengths and limitations
        strengths: List[str] = []
        limitations: List[str] = []

        if s_genetic >= 60.0:
            strengths.append(f"Strong genetic support (score {s_genetic:.1f}/100) reduces clinical phase attrition risk.")
        else:
            limitations.append("Lacks high-confidence human genetic causality or GWAS significance.")

        if s_tractability >= 70.0:
            strengths.append(f"High tractability (score {s_tractability:.1f}/100) with established small-molecule or biologic precedence.")
        elif s_tractability < 40.0:
            limitations.append("Challenging tractability; limited ligandable pockets identified to date.")

        if s_experimental >= 50.0:
            strengths.append(f"Supported by internal in-vitro/CRISPR assay validation (score {s_experimental:.1f}/100).")
        else:
            limitations.append("Lacks internal experimental validation in relevant cellular models.")

        if contradiction_penalty > 0:
            limitations.append(f"Contradictory findings detected across studies (penalty deduction: -{contradiction_penalty:.1f} pts).")

        exp_status = "Validated in-house assays" if records else "No internal experimental data available"
        tract_summary = (
            druggability_profile.summary_rationale
            if druggability_profile and druggability_profile.summary_rationale
            else f"Tractability score: {s_tractability:.1f}/100"
        )

        radar_data = {
            "Disease Association": s_disease,
            "Genetic Rigor": s_genetic,
            "Druggability": s_tractability,
            "Literature": s_literature,
            "Experimental": s_experimental,
            "Safety": s_safety,
        }

        return RankedTarget(
            target_symbol=target.target_symbol,
            target_name=target.target_name,
            disease_name=target.disease_name,
            overall_priority_score=final_clamped,
            confidence_tier=conf_tier,
            confidence_score=conf_score,
            score_breakdown=breakdown,
            evidence_count=len(evidence_items),
            key_pmids=pmids,
            strengths=strengths,
            limitations=limitations,
            experimental_validation_status=exp_status,
            tractability_summary=tract_summary,
            radar_data=radar_data,
        )
