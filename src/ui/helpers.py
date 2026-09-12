from typing import List, Dict, Optional, Any


def get_sample_presets() -> Dict[str, Dict[str, Any]]:
    """Returns curated demonstration research query presets."""
    return {
        "Custom Query": {
            "question": "",
            "disease_name": "",
        },
        "Alzheimer's Disease (TREM2 & BACE1)": {
            "question": "Identify promising therapeutic targets for Alzheimer's disease.",
            "disease_name": "Alzheimer's disease",
        },
        "Parkinson's Disease (SNCA & LRRK2)": {
            "question": "Identify high-confidence therapeutic targets for Parkinson's disease.",
            "disease_name": "Parkinson's disease",
        },
        "Amyotrophic Lateral Sclerosis (SOD1 & TARDBP)": {
            "question": "Prioritize candidate therapeutic targets for Amyotrophic lateral sclerosis.",
            "disease_name": "Amyotrophic lateral sclerosis",
        },
    }


def format_confidence_badge(tier: str) -> str:
    """Returns HTML / markdown colored badge for confidence tiers."""
    t = tier.lower()
    if t == "high":
        return "🟢 High Confidence"
    elif t == "medium":
        return "🔵 Medium Confidence"
    elif t == "low":
        return "🟡 Low Confidence"
    return "⚪ Unconfirmed"


def extract_target_detail(state: Dict[str, Any], target_symbol: str) -> Dict[str, Any]:
    """
    Extracts multi-modal data for a single target from the workflow state.
    """
    if not target_symbol:
        return {}

    # 1. Candidate metadata
    identified = state.get("identified_targets", {}).get(target_symbol, {})

    # 2. Ranking record
    ranking = None
    for r in state.get("target_rankings", []):
        if r.get("target_symbol") == target_symbol:
            ranking = r
            break

    # 3. Evidence items
    evidence = [
        ev for ev in state.get("evidence_records", [])
        if ev.get("target_symbol") == target_symbol
    ]

    # 4. Druggability profile
    druggability = state.get("druggability_assessments", {}).get(target_symbol, {})

    # 5. Experimental validation records
    experimental = state.get("experimental_data_matches", {}).get(target_symbol, [])

    # 6. Compound records
    known_compounds = state.get("known_active_compounds", {}).get(target_symbol, [])
    simulated_compounds = state.get("compound_screenings", {}).get(target_symbol, [])

    return {
        "target_symbol": target_symbol,
        "metadata": identified,
        "ranking": ranking,
        "evidence": evidence,
        "druggability": druggability,
        "experimental": experimental,
        "known_compounds": known_compounds,
        "simulated_compounds": simulated_compounds,
    }


def filter_audit_trace(trace: List[Dict[str, Any]], filter_agent: Optional[str] = None) -> List[Dict[str, Any]]:
    """Filters audit trace entries by agent name."""
    if not trace:
        return []
    if not filter_agent or filter_agent == "All Agents":
        return trace
    return [t for t in trace if t.get("agent_name") == filter_agent]


def prepare_rankings_dataframe(rankings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prepares clean flattened rows for Streamlit table display."""
    rows = []
    for idx, r in enumerate(rankings, start=1):
        sym = r.get("target_symbol", "")
        name = r.get("target_name") or "N/A"
        score = round(r.get("overall_priority_score", 0.0), 1)
        tier = r.get("confidence_tier", "medium").upper()
        tract = r.get("tractability_summary", "Unassessed")
        exp_status = r.get("experimental_validation_status", "None")
        evidence_count = r.get("evidence_count", 0)

        rows.append({
            "Rank": f"#{idx}",
            "Symbol": sym,
            "Target Name": name,
            "Priority Score": score,
            "Confidence Tier": tier,
            "Tractability": tract,
            "Assay Status": exp_status,
            "Evidence Count": evidence_count,
        })
    return rows
