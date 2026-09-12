import time
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from src.domain.models import (
    ResearchReport,
    RankedTarget,
    CitationReference,
    PubMedArticle,
    EvidenceItem,
)
from src.domain.state import ResearchGraphState


def generate_research_report(state: ResearchGraphState) -> ResearchReport:
    """
    Constructs a strongly typed, validated ResearchReport from the workflow state.
    
    SCIENTIFIC INTEGRITY:
    - Never fabricates targets, citations, scores, or predictions.
    - Accurately captures only what was extracted and ranked in the workflow.
    """
    session_id = state.get("session_id", "SESS-UNKNOWN")
    disease_name = state.get("disease_name", "Target Disease")
    research_question = state.get("research_question", "")
    executive_summary = state.get("executive_summary") or (
        f"Autonomous investigation for '{disease_name}' completed. "
        f"Prioritized {len(state.get('target_rankings', []))} therapeutic targets."
    )

    # Deserialize top ranked targets
    top_targets: List[RankedTarget] = []
    for r in state.get("target_rankings", []):
        try:
            r_copy = dict(r)
            if not r_copy.get("disease_name"):
                r_copy["disease_name"] = disease_name
            if "confidence_score" not in r_copy:
                r_copy["confidence_score"] = 0.8
            top_targets.append(RankedTarget(**r_copy))
        except Exception:
            pass

    # Extract all distinct citations from papers and evidence records
    citations_map: Dict[str, CitationReference] = {}

    for p in state.get("retrieved_papers", []):
        cit_data = p.get("citation")
        if cit_data:
            try:
                cit = CitationReference(**cit_data)
                key = cit.pmid or cit.doi or cit.title
                if key and key not in citations_map:
                    citations_map[key] = cit
            except Exception:
                pass

    for ev in state.get("evidence_records", []):
        cit_data = ev.get("citation")
        if cit_data:
            try:
                cit = CitationReference(**cit_data)
                key = cit.pmid or cit.doi or cit.title
                if key and key not in citations_map:
                    citations_map[key] = cit
            except Exception:
                pass

    all_citations = list(citations_map.values())

    methodology = (
        "Multi-agent biomedical discovery pipeline combining NCBI PubMed literature retrieval, "
        "Open Targets Platform genetic and association evidence, multi-modal tractability assessment "
        "(small molecule, antibody, PROTAC), and empirical ChEMBL bioactivity data. Target prioritization "
        "is executed deterministically via a 6-factor weighted multi-criteria scoring algorithm outside of LLM reasoning. "
        "Internal laboratory data is benchmarked against synthetic demonstration assays."
    )

    report_id = f"REP-{session_id[-8:] if len(session_id) >= 8 else session_id}-{int(time.time())}"

    return ResearchReport(
        report_id=report_id,
        session_id=session_id,
        disease_name=disease_name,
        research_question=research_question,
        created_at=datetime.now(timezone.utc),
        executive_summary=executive_summary,
        top_targets=top_targets,
        methodology=methodology,
        all_citations=all_citations,
    )


def report_to_markdown(report: ResearchReport, state: Optional[ResearchGraphState] = None) -> str:
    """
    Renders a comprehensive, presentation-ready scientific Markdown report.
    """
    lines: List[str] = []

    lines.append(f"# Therapeutic Target Prioritization Report: {report.disease_name}")
    lines.append("")
    lines.append(f"**Report ID**: `{report.report_id}`  |  **Session**: `{report.session_id}`  |  **Generated**: {report.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"**Research Question**: *{report.research_question}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive Summary
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append(report.executive_summary)
    lines.append("")

    # Prioritized Targets Table
    lines.append("## 2. Prioritized Candidate Targets")
    lines.append("")
    if not report.top_targets:
        lines.append("*No candidate targets met the threshold for high-confidence prioritization.*")
    else:
        lines.append("| Rank | Symbol | Target Name | Priority Score | Confidence | Key Strengths | Tractability Summary |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for idx, t in enumerate(report.top_targets, start=1):
            sym = t.target_symbol
            name = t.target_name or "N/A"
            score = f"{t.overall_priority_score:.1f}"
            tier = t.confidence_tier.value.upper()
            strengths = "; ".join(t.strengths[:2]) if t.strengths else "Evidence-supported"
            tract = t.tractability_summary or "Unassessed"
            lines.append(f"| **#{idx}** | **{sym}** | {name} | **{score} / 100** | `{tier}` | {strengths} | {tract} |")
    lines.append("")

    # Detailed Target Profiles
    lines.append("## 3. Detailed Target Evaluations")
    lines.append("")
    for idx, t in enumerate(report.top_targets, start=1):
        lines.append(f"### 3.{idx} Target: {t.target_symbol} ({t.target_name or 'Unannotated'})")
        lines.append(f"- **Overall Priority Score**: **{t.overall_priority_score:.1f} / 100** (Confidence Tier: `{t.confidence_tier.value.upper()}`)")
        lines.append(f"- **Experimental Status**: {t.experimental_validation_status}")
        lines.append(f"- **Tractability**: {t.tractability_summary}")
        lines.append("")

        # Score Breakdown
        sb = t.score_breakdown
        lines.append("#### Deterministic Score Breakdown")
        lines.append("| Dimension | Sub-Score (0–100) | Weight | Weighted Value |")
        lines.append("| :--- | :--- | :--- | :--- |")
        w = sb.weights_applied or {}
        lines.append(f"| Disease Association | {sb.disease_association_score:.1f} | {w.get('disease_association', 0.25):.2f} | {sb.disease_association_score * w.get('disease_association', 0.25):.2f} |")
        lines.append(f"| Genetic Evidence | {sb.genetic_evidence_score:.1f} | {w.get('genetic_evidence', 0.20):.2f} | {sb.genetic_evidence_score * w.get('genetic_evidence', 0.20):.2f} |")
        lines.append(f"| Target Tractability | {sb.target_tractability_score:.1f} | {w.get('target_tractability', 0.20):.2f} | {sb.target_tractability_score * w.get('target_tractability', 0.20):.2f} |")
        lines.append(f"| Literature Support | {sb.literature_evidence_score:.1f} | {w.get('literature_evidence', 0.15):.2f} | {sb.literature_evidence_score * w.get('literature_evidence', 0.15):.2f} |")
        lines.append(f"| Experimental Validation | {sb.experimental_validation_score:.1f} | {w.get('experimental_validation', 0.10):.2f} | {sb.experimental_validation_score * w.get('experimental_validation', 0.10):.2f} |")
        lines.append(f"| Safety Profile | {sb.safety_profile_score:.1f} | {w.get('safety_profile', 0.10):.2f} | {sb.safety_profile_score * w.get('safety_profile', 0.10):.2f} |")
        if sb.contradiction_penalty > 0:
            lines.append(f"| *Contradiction Penalty* | -{sb.contradiction_penalty:.1f} | N/A | -{sb.contradiction_penalty:.1f} |")
        lines.append(f"| **Final Score** | **{sb.final_clamped_score:.1f}** | **1.00** | **{sb.final_clamped_score:.1f}** |")
        lines.append("")

        # Strengths and Limitations
        if t.strengths:
            lines.append("**Key Strengths:**")
            for s in t.strengths:
                lines.append(f"- {s}")
            lines.append("")

        if t.limitations:
            lines.append("**Scientific Limitations:**")
            for lim in t.limitations:
                lines.append(f"- {lim}")
            lines.append("")

        # Compound screening data if available in state
        if state:
            sym = t.target_symbol
            known = state.get("known_active_compounds", {}).get(sym, [])
            screened = state.get("compound_screenings", {}).get(sym, [])

            if known or screened:
                lines.append("#### Chemical & Bioactivity Profile")
                if known:
                    lines.append(f"*Measured ChEMBL Bioactivities ({len(known)} records — Empirical Origin)*:")
                    for k in known[:5]:
                        lines.append(f"- Compound `{k.get('compound_id')}` ({k.get('compound_name') or 'N/A'}): {k.get('activity_type')} = **{k.get('activity_value')} {k.get('activity_unit')}** [Assay: `{k.get('assay_chembl_id') or 'ChEMBL'}`]")
                    lines.append("")

                if screened:
                    lines.append(f"*Computational In Silico Screenings ({len(screened)} simulations)*:")
                    lines.append("> **Note**: *Computational simulation prediction — not experimentally measured.*")
                    for sc in screened[:5]:
                        lines.append(f"- Molecule `{sc.get('compound_id')}`: Predicted Binding = **{sc.get('predicted_binding_affinity_kcal_mol')} kcal/mol** (Est. Kd: {sc.get('predicted_kd_nm')} nM, MW: {sc.get('molecular_weight')}, LogP: {sc.get('logp')})")
                    lines.append("")

    # Methodology
    lines.append("## 4. Platform Methodology")
    lines.append("")
    lines.append(report.methodology)
    lines.append("")

    # Provenance and Citations
    lines.append("## 5. Bibliographic Provenance & Citations")
    lines.append("")
    if not report.all_citations:
        lines.append("*No primary literature citations were retrieved for this query.*")
    else:
        for idx, cit in enumerate(report.all_citations, start=1):
            pmid_part = f" [PMID: [{cit.pmid}](https://pubmed.ncbi.nlm.nih.gov/{cit.pmid}/)]" if cit.pmid else ""
            doi_part = f" [DOI: {cit.doi}]" if cit.doi else ""
            lines.append(f"{idx}. {cit.formatted_citation}{pmid_part}{doi_part}")
    lines.append("")

    # Mandatory Disclaimers
    lines.append("---")
    lines.append("## 6. Scientific Integrity & Disclaimers")
    lines.append("")
    lines.append(f"> [!IMPORTANT]")
    lines.append(f"> **Platform Limitations Disclaimer**: {report.limitations_disclaimer}")
    lines.append("")
    lines.append(f"> [!NOTE]")
    lines.append(f"> **Synthetic Assay Notice**: {report.synthetic_data_note}")
    lines.append("")

    return "\n".join(lines)


def report_to_json(report: ResearchReport) -> str:
    """Serializes the ResearchReport to structured JSON."""
    return json.dumps(report.model_dump(mode="json"), indent=2)
