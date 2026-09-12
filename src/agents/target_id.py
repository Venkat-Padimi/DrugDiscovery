import re
import time
from typing import List, Dict, Optional, Set, Any

from src.agents.base import BaseAgent
from src.clients.open_targets import OpenTargetsClient, OpenTargetsApiError
from src.domain.enums import (
    WorkflowStage,
    EvidenceType,
    CausalityLevel,
    StudyType,
    DataOrigin,
)
from src.domain.models import (
    TargetCandidate,
    EvidenceItem,
    CitationReference,
    DruggabilityProfile,
    RankedTarget,
)
from src.domain.normalization import normalizer, GeneIdentifierNormalizer
from src.domain.state import ResearchGraphState
from src.engine.scoring import TargetScoringEngine
from src.engine.experimental_loader import ExperimentalDatasetLoader
from config.settings import settings


class TargetIdentificationAgent(BaseAgent):
    """
    Target Identification Agent.
    
    RESPONSIBILITIES:
    - Extracts candidate therapeutic targets from retrieved literature abstracts and metadata.
    - Normalizes gene symbols to official HGNC nomenclature.
    - Preserves rigorous citation provenance (PMID/PMCID) for every extracted entity.
    - Integrates Open Targets Platform target-disease associations and tractability buckets.
    - Cross-references internal experimental validation assays.
    - Feeds structured multi-modal evidence into the deterministic target-ranking engine.
    - Strictly avoids fabricating target claims, scores, or associations.
    """

    # Gene symbol extraction pattern: 2 to 6 uppercase letters and digits (e.g., APP, TREM2, BACE1, CDK4)
    # Excludes common non-gene abbreviations
    _NON_GENE_STOPWORDS = {
        "DNA", "RNA", "MRNA", "CNS", "CSF", "PET", "MRI", "FDA", "NIH", "USA",
        "AND", "FOR", "THE", "NOT", "ALL", "NEW", "TWO", "ONE", "WHO", "CAN",
        "AGE", "ACT", "SET", "MAP", "KEY", "TOP", "LOW", "DRUG", "CELL", "CORE",
    }

    def __init__(
        self,
        open_targets_client: Optional[OpenTargetsClient] = None,
        scoring_engine: Optional[TargetScoringEngine] = None,
        gene_normalizer: Optional[GeneIdentifierNormalizer] = None,
        experimental_loader: Optional[ExperimentalDatasetLoader] = None,
        agent_name: str = "TargetIdentificationAgent",
    ):
        super().__init__(agent_name=agent_name, stage=WorkflowStage.TARGET_IDENTIFICATION)
        self.ot_client = open_targets_client or OpenTargetsClient()
        self.scoring_engine = scoring_engine or TargetScoringEngine()
        self.normalizer = gene_normalizer or normalizer
        
        # Load synthetic experimental dataset if available
        self.exp_loader = experimental_loader
        if self.exp_loader is None and settings.synthetic_data_path.exists():
            try:
                loader = ExperimentalDatasetLoader(settings.synthetic_data_path)
                loader.load()
                self.exp_loader = loader
            except Exception:
                self.exp_loader = None

    def extract_targets_from_text(self, text: str) -> List[str]:
        """
        Extracts candidate gene/target symbols from text using high-precision regex and alias mapping.
        """
        if not text:
            return []

        # Find potential uppercase gene symbol tokens
        tokens = re.findall(r"\b[A-Z0-9\-]{2,8}\b", text)
        extracted: Set[str] = set()

        for token in tokens:
            clean = token.strip("-").upper()
            if clean in self._NON_GENE_STOPWORDS or len(clean) < 2:
                continue

            # Check if token can be normalized to a known reference gene
            canonical = self.normalizer.normalize_symbol(clean)
            if canonical and canonical not in self._NON_GENE_STOPWORDS:
                # If it's a known reference target or matches standard HGNC pattern (letters followed optionally by digits)
                if re.match(r"^[A-Z]+[0-9]*[A-Z0-9]*$", canonical):
                    extracted.add(canonical)

        return sorted(list(extracted))

    def run(self, state: ResearchGraphState) -> ResearchGraphState:
        """
        Executes target identification, Open Targets integration, and deterministic ranking.
        """
        start_time = time.monotonic()
        disease_name = state.get("disease_name", "")
        retrieved_papers = state.get("retrieved_papers", [])
        tool_calls: List[str] = []

        identified_targets: Dict[str, TargetCandidate] = {}
        all_evidence: List[EvidenceItem] = []
        ot_association_scores: Dict[str, float] = {}

        # Step 1: Literature Target Extraction
        for paper_dict in retrieved_papers:
            pmid = paper_dict.get("pmid", "")
            title = paper_dict.get("title", "")
            abstract = paper_dict.get("abstract", "")
            citation_dict = paper_dict.get("citation")
            citation = CitationReference(**citation_dict) if citation_dict else None

            combined_text = f"{title} {abstract}"
            extracted_symbols = self.extract_targets_from_text(combined_text)

            for sym in extracted_symbols:
                canonical = self.normalizer.normalize_symbol(sym)
                if not canonical:
                    continue

                if canonical not in identified_targets:
                    identified_targets[canonical] = TargetCandidate(
                        target_symbol=canonical,
                        target_name=self.normalizer.get_known_approved_name(canonical),
                        ensembl_id=self.normalizer.get_known_ensembl_id(canonical),
                        disease_name=disease_name,
                        disease_efo_id=state.get("disease_efo_id"),
                        identification_sources=["Literature"],
                        initial_rationale=f"Extracted from biomedical literature (PMID: {pmid}).",
                    )
                else:
                    if "Literature" not in identified_targets[canonical].identification_sources:
                        identified_targets[canonical].identification_sources.append("Literature")

                # Create literature evidence item
                ev_id = f"EV-LIT-{pmid}-{canonical}"
                evidence_item = EvidenceItem(
                    evidence_id=ev_id,
                    target_symbol=canonical,
                    target_ensembl_id=identified_targets[canonical].ensembl_id,
                    disease_name=disease_name,
                    disease_efo_id=state.get("disease_efo_id"),
                    evidence_type=EvidenceType.LITERATURE_COOCCURRENCE,
                    causality_level=CausalityLevel.FUNCTIONAL_ASSOCIATION,
                    study_type=StudyType.IN_VITRO_CELLULAR,
                    confidence_score=0.80,
                    data_origin=DataOrigin.LITERATURE_RETRIEVAL,
                    source_database="PubMed",
                    citation=citation,
                    extracted_statement=f"Candidate target {canonical} identified in publication: '{title}'.",
                )
                all_evidence.append(evidence_item)

        # Step 2: Open Targets Disease Mapping & Associated Targets
        disease_efo = state.get("disease_efo_id")
        try:
            if not disease_efo and disease_name:
                tool_calls.append(f"open_targets.search_disease('{disease_name}')")
                disease_info = self.ot_client.search_disease(disease_name)
                if disease_info:
                    disease_efo = disease_info.get("id")
                    state["disease_efo_id"] = disease_efo

            if disease_efo:
                tool_calls.append(f"open_targets.get_associated_targets('{disease_efo}')")
                associated_targets = self.ot_client.get_associated_targets(disease_efo, size=15)

                for at in associated_targets:
                    raw_sym = at.get("approved_symbol", "")
                    canonical = self.normalizer.normalize_symbol(raw_sym)
                    if not canonical:
                        continue

                    ensembl_id = at.get("ensembl_id")
                    ot_score = at.get("overall_score", 0.0)
                    ot_association_scores[canonical] = ot_score
                    datatype_scores = at.get("datatype_scores", {})
                    genetic_score = datatype_scores.get("genetic_association", 0.0)

                    if canonical not in identified_targets:
                        identified_targets[canonical] = TargetCandidate(
                            target_symbol=canonical,
                            target_name=at.get("approved_name") or self.normalizer.get_known_approved_name(canonical),
                            ensembl_id=ensembl_id or self.normalizer.get_known_ensembl_id(canonical),
                            disease_name=disease_name,
                            disease_efo_id=disease_efo,
                            identification_sources=["OpenTargets"],
                            initial_rationale=f"Associated in Open Targets (Overall score: {ot_score:.2f}).",
                        )
                    else:
                        if "OpenTargets" not in identified_targets[canonical].identification_sources:
                            identified_targets[canonical].identification_sources.append("OpenTargets")
                        if not identified_targets[canonical].ensembl_id:
                            identified_targets[canonical].ensembl_id = ensembl_id

                    # Create Open Targets Evidence Item
                    ev_type = EvidenceType.GENETIC_ASSOCIATION if genetic_score > 0 else EvidenceType.PATHWAY_PERTURBATION
                    causal_lvl = (
                        CausalityLevel.CAUSAL_DEMONSTRATED if genetic_score >= 0.8
                        else CausalityLevel.FUNCTIONAL_ASSOCIATION
                    )
                    ev_ot = EvidenceItem(
                        evidence_id=f"EV-OT-{canonical}-{disease_efo}",
                        target_symbol=canonical,
                        target_ensembl_id=ensembl_id,
                        disease_name=disease_name,
                        disease_efo_id=disease_efo,
                        evidence_type=ev_type,
                        causality_level=causal_lvl,
                        study_type=StudyType.HUMAN_GWAS if genetic_score > 0 else StudyType.IN_VITRO_CELLULAR,
                        confidence_score=round(min(1.0, max(0.1, ot_score)), 2),
                        data_origin=DataOrigin.EXPERIMENTALLY_MEASURED,
                        source_database="OpenTargets",
                        extracted_statement=(
                            f"Open Targets association score: {ot_score:.2f} "
                            f"(Genetic: {genetic_score:.2f}, Literature: {datatype_scores.get('literature', 0.0):.2f})"
                        ),
                    )
                    all_evidence.append(ev_ot)

        except OpenTargetsApiError as e:
            self.record_error(
                state=state,
                error_type="OpenTargetsApiError",
                message=f"Open Targets integration error: {e}",
                degradation_applied=True,
            )

        # Step 3: Fetch Target Tractability / Druggability
        druggability_dict: Dict[str, DruggabilityProfile] = {}
        for sym, cand in identified_targets.items():
            ensembl_id = cand.ensembl_id or self.normalizer.get_known_ensembl_id(sym)
            if ensembl_id:
                try:
                    tool_calls.append(f"open_targets.get_target_tractability('{ensembl_id}')")
                    profile = self.ot_client.get_target_tractability(ensembl_id, sym)
                    if isinstance(profile, DruggabilityProfile):
                        druggability_dict[sym] = profile
                    else:
                        druggability_dict[sym] = DruggabilityProfile(
                            target_symbol=sym,
                            overall_tractability_score=25.0,
                            summary_rationale="Fallback tractability profile.",
                        )
                except OpenTargetsApiError:
                    druggability_dict[sym] = DruggabilityProfile(
                        target_symbol=sym,
                        overall_tractability_score=30.0,
                        summary_rationale="Open Targets tractability query degraded.",
                    )
            else:
                druggability_dict[sym] = DruggabilityProfile(
                    target_symbol=sym,
                    overall_tractability_score=25.0,
                    summary_rationale="Unassessed tractability; no Ensembl ID mapped.",
                )

        # Step 4: Experimental Data Matching
        exp_matches: Dict[str, List[Any]] = {}
        if self.exp_loader:
            for sym in identified_targets.keys():
                matches = self.exp_loader.find_by_target(sym)
                if matches:
                    exp_matches[sym] = matches

        # Step 5: Deterministic Target Ranking
        ranked_targets: List[RankedTarget] = []
        for sym, cand in identified_targets.items():
            sym_evidence = [ev for ev in all_evidence if ev.target_symbol == sym]
            sym_tractability = druggability_dict.get(sym)
            sym_exp = exp_matches.get(sym, [])
            ot_score = ot_association_scores.get(sym)

            ranked = self.scoring_engine.rank_target(
                target=cand,
                evidence_items=sym_evidence,
                druggability_profile=sym_tractability,
                experimental_records=sym_exp,
                open_targets_overall_score=ot_score,
            )
            ranked_targets.append(ranked)

        # Sort targets deterministically by priority score descending
        ranked_targets.sort(key=lambda t: t.overall_priority_score, reverse=True)

        # Step 6: Update State
        state["identified_targets"] = {s: c.model_dump() for s, c in identified_targets.items()}
        state["evidence_records"] = [ev.model_dump() for ev in all_evidence]
        state["druggability_assessments"] = {s: p.model_dump() for s, p in druggability_dict.items()}
        state["experimental_data_matches"] = {s: [r.model_dump() for r in recs] for s, recs in exp_matches.items()}
        state["target_rankings"] = [r.model_dump() for r in ranked_targets]
        state["current_stage"] = self.stage.value

        duration_ms = (time.monotonic() - start_time) * 1000.0

        self.record_trace(
            state=state,
            input_summary=f"Papers: {len(retrieved_papers)}, Disease: '{disease_name}'",
            output_summary=f"Identified {len(identified_targets)} targets, {len(all_evidence)} evidence items, ranked {len(ranked_targets)} targets",
            tool_calls=tool_calls,
            duration_ms=duration_ms,
            status="success" if identified_targets else "degraded",
            notes="Target identification, Open Targets evidence synthesis, and deterministic ranking complete.",
        )

        return state
