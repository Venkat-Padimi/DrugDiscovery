from typing import List, Dict, Optional, Any
import plotly.graph_objects as go
import plotly.express as px


def render_target_ranking_chart(rankings: List[Dict[str, Any]]) -> Optional[go.Figure]:
    """
    Renders an interactive horizontal bar chart comparing ranked targets.
    
    Zero fabrication: only plots real candidate targets from state.
    """
    if not rankings:
        return None

    # Reverse list so highest score is at the top of the horizontal bar chart
    sorted_rankings = sorted(rankings, key=lambda x: x.get("overall_priority_score", 0.0))

    symbols = [r.get("target_symbol", "Unknown") for r in sorted_rankings]
    scores = [round(r.get("overall_priority_score", 0.0), 1) for r in sorted_rankings]
    tiers = [r.get("confidence_tier", "medium").upper() for r in sorted_rankings]

    tier_colors = {
        "HIGH": "#10b981",    # emerald green
        "MEDIUM": "#3b82f6",  # blue
        "LOW": "#f59e0b",     # amber
        "UNCONFIRMED": "#94a3b8"  # slate
    }
    colors = [tier_colors.get(t, "#3b82f6") for t in tiers]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=symbols,
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(color="#1e293b", width=1),
            ),
            text=[f"{s} ({t})" for s, t in zip(scores, tiers)],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Score: %{x}/100<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="Deterministic Target Priority Scores",
            font=dict(size=16, color="#0f172a"),
        ),
        xaxis=dict(
            title="Composite Priority Score (0–100)",
            range=[0, 100],
            gridcolor="#e2e8f0",
        ),
        yaxis=dict(
            title="Candidate Target",
            autorange=True,
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=80, r=30, t=50, b=50),
        height=max(280, len(symbols) * 45),
    )

    return fig


def render_radar_chart(radar_data: Dict[str, float], target_symbol: str) -> Optional[go.Figure]:
    """
    Renders an interactive radar / spider chart across 6 scientific evidence dimensions.
    """
    if not radar_data:
        return None

    dimension_labels = {
        "disease_association": "Disease Association",
        "genetic_evidence": "Genetic Evidence",
        "target_tractability": "Tractability",
        "literature_evidence": "Literature Support",
        "experimental_validation": "Internal Validation",
        "safety_profile": "Safety Profile",
    }

    categories = [dimension_labels.get(k, k.replace("_", " ").title()) for k in radar_data.keys()]
    values = [round(v, 1) for v in radar_data.values()]

    # Close the radar loop
    if categories and values:
        categories.append(categories[0])
        values.append(values[0])

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(14, 165, 233, 0.25)",
            line=dict(color="#0284c7", width=2.5),
            name=target_symbol,
            hovertemplate="<b>%{theta}</b>: %{r}/100<extra></extra>",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[20, 40, 60, 80, 100],
                gridcolor="#cbd5e1",
            ),
            angularaxis=dict(
                gridcolor="#cbd5e1",
            ),
            bgcolor="#f8fafc",
        ),
        title=dict(
            text=f"Evidence Dimension Profile: {target_symbol}",
            font=dict(size=15, color="#0f172a"),
        ),
        margin=dict(l=60, r=60, t=50, b=40),
        height=380,
        showlegend=False,
    )

    return fig


def render_evidence_distribution_chart(evidence_items: List[Dict[str, Any]]) -> Optional[go.Figure]:
    """
    Renders a donut chart of evidence modalities retrieved for candidate targets.
    """
    if not evidence_items:
        return None

    type_counts: Dict[str, int] = {}
    for item in evidence_items:
        ev_type = item.get("evidence_type", "literature_cooccurrence")
        label = ev_type.replace("_", " ").title()
        type_counts[label] = type_counts.get(label, 0) + 1

    labels = list(type_counts.keys())
    values = list(type_counts.values())

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker=dict(colors=px.colors.qualitative.Prism),
            hovertemplate="<b>%{label}</b><br>Count: %{value} (%{percent})<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text="Evidence Modality Distribution",
            font=dict(size=15, color="#0f172a"),
        ),
        margin=dict(l=30, r=30, t=50, b=30),
        height=320,
        legend=dict(orientation="h", y=-0.1),
    )

    return fig


def render_compound_bioactivity_chart(
    known_compounds: List[Dict[str, Any]],
    simulated_compounds: List[Dict[str, Any]],
    target_symbol: str,
) -> Optional[go.Figure]:
    """
    Visualizes compound bioactivities while maintaining strict separation between
    empirically measured assays (ChEMBL) and in silico simulations.
    
    SCIENTIFIC RULE:
    Measured assays and computational predictions use distinct traces and explicit disclaimers.
    """
    if not known_compounds and not simulated_compounds:
        return None

    fig = go.Figure()

    # 1. Measured empirical compounds (IC50 / Ki in nM)
    if known_compounds:
        meas_names = [
            f"{c.get('compound_name') or c.get('compound_id')} ({c.get('activity_type', 'IC50')})"
            for c in known_compounds[:6]
        ]
        meas_vals = [c.get("activity_value", 0.0) for c in known_compounds[:6]]

        fig.add_trace(
            go.Bar(
                name="ChEMBL Measured (Empirical)",
                x=meas_names,
                y=meas_vals,
                marker=dict(color="#059669", line=dict(color="#064e3b", width=1)),
                hovertemplate="<b>%{x}</b><br>Measured: %{y} nM<br><i>Empirical Wet-Lab Assay</i><extra></extra>",
            )
        )

    # 2. In silico predicted Kd (nM)
    if simulated_compounds:
        sim_names = [
            f"{c.get('compound_id')} (Simulated)"
            for c in simulated_compounds[:6]
        ]
        sim_vals = [c.get("predicted_kd_nm", 1000.0) for c in simulated_compounds[:6]]

        fig.add_trace(
            go.Bar(
                name="In Silico Simulation (Predicted Kd)",
                x=sim_names,
                y=sim_vals,
                marker=dict(color="#6366f1", line=dict(color="#312e81", width=1)),
                hovertemplate="<b>%{x}</b><br>Predicted Kd: %{y} nM<br><i>Computational Simulation — Not Experimentally Measured</i><extra></extra>",
            )
        )

    fig.update_layout(
        title=dict(
            text=f"Chemical Bioactivity & In Silico Screening: {target_symbol}",
            font=dict(size=15, color="#0f172a"),
        ),
        yaxis=dict(
            title="Activity / Affinity (nM) — Log Scale",
            type="log",
            gridcolor="#e2e8f0",
        ),
        xaxis=dict(
            tickangle=-25,
        ),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        margin=dict(l=60, r=30, t=50, b=80),
        height=380,
        legend=dict(orientation="h", y=1.12),
        barmode="group",
    )

    return fig
