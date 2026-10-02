"""
Deterministic Graph Builder for React Flow Target Discovery Network.
Constructs typed nodes and labeled relational edges strictly from real ResearchGraphState.
Zero data fabrication: only links verified entities retrieved during workflow execution.
"""
from typing import Dict, Any, List


def build_discovery_graph(state: Dict[str, Any], max_targets: int = 6) -> Dict[str, Any]:
    """
    Constructs a layered React Flow graph representation from workflow state:
    Disease -> Targets -> Evidence & Tractability -> Compounds
    """
    if not state:
        return {"nodes": [], "edges": []}

    disease_name = state.get("disease_name") or state.get("research_question") or "Target Pathology"
    rankings = state.get("target_rankings", [])
    if not rankings:
        # If no rankings yet, return just disease root
        return {
            "nodes": [
                {
                    "id": "node-disease-root",
                    "type": "diseaseNode",
                    "position": {"x": 400, "y": 40},
                    "data": {
                        "label": disease_name,
                        "entity": disease_name,
                        "status": state.get("status", "pending"),
                    },
                }
            ],
            "edges": [],
        }

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Root Disease Node
    disease_node_id = "node-disease"
    nodes.append({
        "id": disease_node_id,
        "type": "diseaseNode",
        "position": {"x": 500, "y": 30},
        "data": {
            "label": disease_name,
            "entity": disease_name,
            "session_id": state.get("session_id", ""),
            "total_targets": len(rankings),
        },
    })

    top_targets = rankings[:max_targets]
    spacing_x = 320
    base_x = max(50, 500 - (len(top_targets) * spacing_x) // 2)

    evidence_records = state.get("evidence_records", [])
    druggability_dict = state.get("druggability_assessments", {})
    known_compounds_dict = state.get("known_active_compounds", {})
    screenings_dict = state.get("compound_screenings", {})

    for t_idx, r in enumerate(top_targets):
        sym = r.get("target_symbol", f"TARGET_{t_idx}")
        score = round(r.get("overall_priority_score", 0.0), 1)
        tier = r.get("confidence_tier", "medium").upper()
        target_name = r.get("target_name") or sym

        target_node_id = f"node-target-{sym}"
        target_x = base_x + (t_idx * spacing_x)
        target_y = 200

        # 2. Target Node
        nodes.append({
            "id": target_node_id,
            "type": "targetNode",
            "position": {"x": target_x, "y": target_y},
            "data": {
                "symbol": sym,
                "name": target_name,
                "score": score,
                "tier": tier,
                "tractability": r.get("tractability_summary", "Unassessed"),
                "assay_status": r.get("experimental_validation_status", "None"),
            },
        })

        # Edge: Disease -> Target
        edges.append({
            "id": f"edge-disease-{sym}",
            "source": disease_node_id,
            "target": target_node_id,
            "label": "ASSOCIATED_WITH",
            "animated": True,
            "data": {"relationship": "ASSOCIATED_WITH"},
        })

        # 3. Evidence Nodes (top 2 supporting/contradicting items, spaced comfortably)
        target_ev = [ev for ev in evidence_records if ev.get("target_symbol") == sym][:2]
        for e_idx, ev in enumerate(target_ev):
            ev_id = f"node-ev-{sym}-{e_idx}"
            is_contradictory = bool(ev.get("is_contradictory", False))
            citation = ev.get("citation", {})
            pmid = citation.get("pmid") or ev.get("source_database", "PubMed")
            rel_label = "CONTRADICTED_BY" if is_contradictory else "SUPPORTED_BY"

            nodes.append({
                "id": ev_id,
                "type": "evidenceNode",
                "position": {"x": target_x - 75 + (e_idx * 150), "y": target_y + 180},
                "data": {
                    "target_symbol": sym,
                    "evidence_type": ev.get("evidence_type", "literature_cooccurrence"),
                    "pmid": pmid,
                    "title": citation.get("title", "Evidence Reference"),
                    "causality": ev.get("causality_level", "functional_association"),
                    "is_contradictory": is_contradictory,
                },
            })

            edges.append({
                "id": f"edge-ev-{sym}-{e_idx}",
                "source": target_node_id,
                "target": ev_id,
                "label": rel_label,
                "data": {"relationship": rel_label},
            })

        # 4. Druggability Node
        drug_info = druggability_dict.get(sym, {})
        if drug_info:
            drug_node_id = f"node-drug-{sym}"
            nodes.append({
                "id": drug_node_id,
                "type": "druggabilityNode",
                "position": {"x": target_x + 40, "y": target_y + 360},
                "data": {
                    "target_symbol": sym,
                    "tractability_score": round(drug_info.get("overall_tractability_score", 0.0), 1),
                    "modalities": list(drug_info.get("modalities", {}).keys()),
                },
            })

            edges.append({
                "id": f"edge-drug-{sym}",
                "source": target_node_id,
                "target": drug_node_id,
                "label": "TRACTABILITY_OF",
                "data": {"relationship": "TRACTABILITY_OF"},
            })

        # 5. Compound Node (empirical ChEMBL binder or top simulated compound)
        known_list = known_compounds_dict.get(sym, [])
        sim_list = screenings_dict.get(sym, [])

        if known_list:
            top_chembl = known_list[0]
            compound_node_id = f"node-compound-known-{sym}"
            nodes.append({
                "id": compound_node_id,
                "type": "compoundNode",
                "position": {"x": target_x - 60, "y": target_y + 490},
                "data": {
                    "target_symbol": sym,
                    "compound_id": top_chembl.get("compound_id"),
                    "compound_name": top_chembl.get("compound_name") or top_chembl.get("compound_id"),
                    "is_empirical": True,
                    "activity": f"{top_chembl.get('activity_type', 'IC50')}={top_chembl.get('activity_value')} {top_chembl.get('activity_unit', 'nM')}",
                    "disclaimer": "Empirically measured bioactivity (ChEMBL)",
                },
            })

            edges.append({
                "id": f"edge-compound-known-{sym}",
                "source": compound_node_id,
                "target": target_node_id,
                "label": "TARGET_OF",
                "data": {"relationship": "TARGET_OF"},
            })

        elif sim_list:
            top_sim = sim_list[0]
            compound_node_id = f"node-compound-sim-{sym}"
            nodes.append({
                "id": compound_node_id,
                "type": "compoundNode",
                "position": {"x": target_x - 60, "y": target_y + 490},
                "data": {
                    "target_symbol": sym,
                    "compound_id": top_sim.get("compound_id"),
                    "compound_name": top_sim.get("compound_id"),
                    "is_empirical": False,
                    "predicted_kd": f"Est. Kd: {top_sim.get('predicted_kd_nm')} nM",
                    "disclaimer": "Computational simulation prediction — not experimentally measured.",
                },
            })

            edges.append({
                "id": f"edge-compound-sim-{sym}",
                "source": compound_node_id,
                "target": target_node_id,
                "label": "SCREENED_AGAINST",
                "data": {"relationship": "SCREENED_AGAINST"},
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "disease": disease_name,
            "target_count": len(top_targets),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        },
    }
