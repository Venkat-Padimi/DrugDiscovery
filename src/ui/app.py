import time
import uuid
import streamlit as st
import pandas as pd

from src.domain.state import create_initial_state, ResearchGraphState
from src.domain.enums import WorkflowStage, DataOrigin
from src.engine.workflow import ResearchWorkflowRunner
from src.engine.reporter import generate_research_report, report_to_markdown, report_to_json
from src.ui.helpers import (
    get_sample_presets,
    format_confidence_badge,
    extract_target_detail,
    filter_audit_trace,
    prepare_rankings_dataframe,
)
from src.ui.visualizations import (
    render_target_ranking_chart,
    render_radar_chart,
    render_evidence_distribution_chart,
    render_compound_bioactivity_chart,
)


def init_session():
    """Initializes Streamlit session state."""
    if "investigation_state" not in st.session_state:
        st.session_state["investigation_state"] = None
    if "is_running" not in st.session_state:
        st.session_state["is_running"] = False
    if "selected_target" not in st.session_state:
        st.session_state["selected_target"] = None
    if "active_preset" not in st.session_state:
        st.session_state["active_preset"] = "Alzheimer's Disease (TREM2 & BACE1)"


def render_pipeline_stepper(current_stage: str, has_errors: bool = False, is_degraded: bool = False):
    """Renders a responsive visual pipeline stage stepper."""
    stages = [
        ("Supervisor Plan", "INITIALIZATION"),
        ("Literature Search", "LITERATURE_SEARCH"),
        ("Target Identification", "TARGET_IDENTIFICATION"),
        ("Evidence Evaluation", "EVIDENCE_EVALUATION"),
        ("Druggability", "TRACTABILITY_ASSESSMENT"),
        ("Deterministic Ranking", "TARGET_RANKING"),
        ("Compound Screening", "COMPOUND_SCREENING"),
        ("Synthesis & Report", "COMPLETED"),
    ]

    cols = st.columns(len(stages))
    for idx, (col, (name, stage_key)) in enumerate(zip(cols, stages)):
        with col:
            is_active = (current_stage == stage_key.lower() or current_stage == stage_key)
            is_done = current_stage == "completed" or (st.session_state["investigation_state"] is not None)

            if is_degraded and is_active:
                st.markdown(
                    f"<div style='background-color:#fef3c7; border:1px solid #f59e0b; border-radius:6px; padding:6px; text-align:center; font-size:11px; font-weight:600; color:#92400e;'>"
                    f"⚠️ {idx+1}. {name}</div>",
                    unsafe_allow_html=True,
                )
            elif is_active:
                st.markdown(
                    f"<div style='background-color:#dbeafe; border:1px solid #3b82f6; border-radius:6px; padding:6px; text-align:center; font-size:11px; font-weight:600; color:#1e40af;'>"
                    f"🔄 {idx+1}. {name}</div>",
                    unsafe_allow_html=True,
                )
            elif is_done:
                st.markdown(
                    f"<div style='background-color:#ecfdf5; border:1px solid #10b981; border-radius:6px; padding:6px; text-align:center; font-size:11px; font-weight:600; color:#065f46;'>"
                    f"✓ {idx+1}. {name}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='background-color:#f8fafc; border:1px solid #cbd5e1; border-radius:6px; padding:6px; text-align:center; font-size:11px; color:#64748b;'>"
                    f"{idx+1}. {name}</div>",
                    unsafe_allow_html=True,
                )


def run_workflow_investigation(
    question: str,
    disease_name: str,
    enable_compound_screening: bool,
    top_n: int,
    max_lit: int,
    weights: dict,
):
    """Executes the multi-agent investigation and saves state to session."""
    session_id = f"UI-{uuid.uuid4().hex[:8].upper()}"
    init_state = create_initial_state(
        session_id=session_id,
        research_question=question,
        disease_name=disease_name,
        scoring_weights=weights,
        enable_compound_screening=enable_compound_screening,
        max_literature_results=max_lit,
    )
    init_state["top_n_targets_to_screen"] = top_n

    runner = ResearchWorkflowRunner()
    with st.spinner(f"Executing autonomous research investigation for '{disease_name or question}'..."):
        final_state = runner.run(init_state)

    st.session_state["investigation_state"] = final_state
    rankings = final_state.get("target_rankings", [])
    if rankings:
        st.session_state["selected_target"] = rankings[0].get("target_symbol")


def main():
    st.set_page_config(
        page_title="Drug Discovery & Target Identification Agent",
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session()

    # Top Header
    st.title("🧬 Drug Discovery & Target Identification Agent")
    st.caption(
        "Autonomous agentic AI research platform for biomedical literature search, target identification, "
        "multi-modal evidence evaluation, tractability assessment, and deterministic prioritization."
    )

    presets = get_sample_presets()

    # --- SIDEBAR CONTROLS ---
    with st.sidebar:
        st.header("🔬 Investigation Setup")

        # Preset selector
        selected_preset = st.selectbox(
            "Select Demonstration Preset",
            options=list(presets.keys()),
            index=list(presets.keys()).index(st.session_state["active_preset"]),
            help="Choose a pre-configured disease query to explore the platform.",
        )
        st.session_state["active_preset"] = selected_preset
        preset_vals = presets[selected_preset]

        question_input = st.text_area(
            "Research Question",
            value=preset_vals["question"] or "Identify promising therapeutic targets for Alzheimer's disease.",
            height=90,
            help="Specify the disease or biological question you wish the agents to investigate.",
        )

        disease_input = st.text_input(
            "Target Disease Entity (Optional)",
            value=preset_vals["disease_name"] or "",
            placeholder="e.g. Alzheimer's disease",
            help="Leave blank to let the Supervisor Agent auto-extract the disease.",
        )

        with st.expander("⚙️ Advanced Pipeline Parameters", expanded=False):
            enable_compound_screening = st.checkbox(
                "Enable Compound Screening Layer",
                value=True,
                help="Retrieves ChEMBL bioactivities and executes in silico affinity simulations.",
            )
            top_n_screen = st.slider(
                "Top Targets to Screen for Compounds",
                min_value=1,
                max_value=10,
                value=5,
            )
            max_lit_results = st.slider(
                "Max Literature Results (PubMed)",
                min_value=5,
                max_value=30,
                value=15,
            )

            st.markdown("**Deterministic Scoring Weights** (Sum = 1.0):")
            w_disease = st.number_input("Disease Association", 0.0, 1.0, 0.25, step=0.05)
            w_genetics = st.number_input("Genetic Evidence", 0.0, 1.0, 0.20, step=0.05)
            w_tract = st.number_input("Target Tractability", 0.0, 1.0, 0.20, step=0.05)
            w_lit = st.number_input("Literature Support", 0.0, 1.0, 0.15, step=0.05)
            w_exp = st.number_input("Internal Assays", 0.0, 1.0, 0.10, step=0.05)
            w_safety = st.number_input("Safety Profile", 0.0, 1.0, 0.10, step=0.05)

            scoring_weights = {
                "disease_association": w_disease,
                "genetic_evidence": w_genetics,
                "target_tractability": w_tract,
                "literature_evidence": w_lit,
                "experimental_validation": w_exp,
                "safety_profile": w_safety,
            }

        launch_button = st.button(
            "🚀 Launch Investigation",
            type="primary",
            use_container_width=True,
            disabled=st.session_state["is_running"],
        )

        st.markdown("---")
        st.markdown(
            "<div style='font-size:11px; color:#64748b; line-height:1.4;'>"
            "<b>Scientific Integrity Guarantees</b>:<br>"
            "• Zero hallucinated PMIDs, genes, or affinities<br>"
            "• Deterministic composite scoring outside of LLM<br>"
            "• Strict 4-tier segregation of evidence<br>"
            "• Mandatory computational simulation disclaimers"
            "</div>",
            unsafe_allow_html=True,
        )

    # --- INVESTIGATION EXECUTION TRIGGER ---
    if launch_button:
        if not question_input.strip():
            st.error("Please provide a biomedical research question.")
        else:
            run_workflow_investigation(
                question=question_input.strip(),
                disease_name=disease_input.strip(),
                enable_compound_screening=enable_compound_screening,
                top_n=top_n_screen,
                max_lit=max_lit_results,
                weights=scoring_weights,
            )
            st.rerun()

    # --- MAIN CONTENT AREA ---
    state = st.session_state.get("investigation_state")

    if state is None:
        # Default placeholder landing view
        st.info("👋 Welcome! Select a research query preset from the sidebar and click **Launch Investigation** to begin.")

        render_pipeline_stepper("INITIALIZATION")
        st.markdown("### Platform Architecture & Modalities")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 📚 Multi-Source Evidence")
            st.write("Retrieves verified PubMed/PMC scientific literature with PMIDs, DOIs, and Open Targets genetic associations.")
        with c2:
            st.markdown("#### ⚖️ Deterministic Prioritization")
            st.write("Evaluates causality vs correlation, flags contradictory findings, and calculates explainable 6-dimension scores.")
        with c3:
            st.markdown("#### 🧪 Compound & Bioactivity")
            st.write("Queries empirical ChEMBL bioactivities and computes in silico binding simulations with mandatory disclaimers.")
        return

    # --- ACTIVE INVESTIGATION RESULTS DISPLAY ---
    current_stage = state.get("current_stage", "completed")
    errors = state.get("errors", [])
    is_degraded = state.get("status") == "degraded" or any(e.get("degradation_applied") for e in errors)

    render_pipeline_stepper(current_stage, has_errors=bool(errors), is_degraded=is_degraded)
    st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

    if is_degraded:
        st.warning(
            "⚠️ **Degraded Execution Notice**: One or more external endpoints encountered transient failures. "
            "Automated fallbacks were applied cleanly without interrupting the investigation. See Audit Trace tab for details."
        )

    # Key Metrics Banner
    rankings = state.get("target_rankings", [])
    papers = state.get("retrieved_papers", [])
    evidence = state.get("evidence_records", [])

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Disease Entity", state.get("disease_name") or "Auto-extracted")
    with m2:
        st.metric("PubMed Papers", len(papers))
    with m3:
        st.metric("Evidence Items", len(evidence))
    with m4:
        st.metric("Prioritized Targets", len(rankings))
    with m5:
        top_score = f"{rankings[0]['overall_priority_score']:.1f}/100" if rankings else "N/A"
        st.metric("Top Score", top_score)

    # Executive Overview Box
    if state.get("executive_summary"):
        with st.expander("📝 Executive Synthesis Overview", expanded=True):
            st.markdown(state["executive_summary"])

    # Tabs
    tab_rankings, tab_detail, tab_report, tab_trace = st.tabs([
        "🏆 Target Rankings",
        "🔍 Target Deep Dive",
        "📋 Research Report & Export",
        "🕵️ Agent Audit Trace",
    ])

    # --- TAB 1: TARGET RANKINGS ---
    with tab_rankings:
        if not rankings:
            st.info("No targets met the prioritization threshold for this query.")
        else:
            col_chart, col_dist = st.columns([3, 2])
            with col_chart:
                fig_bar = render_target_ranking_chart(rankings)
                if fig_bar:
                    st.plotly_chart(fig_bar, use_container_width=True)
            with col_dist:
                fig_dist = render_evidence_distribution_chart(evidence)
                if fig_dist:
                    st.plotly_chart(fig_dist, use_container_width=True)

            st.markdown("#### Prioritized Candidates Table")
            df_rows = prepare_rankings_dataframe(rankings)
            st.dataframe(pd.DataFrame(df_rows), use_container_width=True, hide_index=True)

    # --- TAB 2: TARGET DEEP DIVE ---
    with tab_detail:
        if not rankings:
            st.info("No targets available to inspect.")
        else:
            target_symbols = [r["target_symbol"] for r in rankings]
            current_selected = st.session_state.get("selected_target")
            selected_idx = target_symbols.index(current_selected) if current_selected in target_symbols else 0

            chosen_symbol = st.selectbox(
                "Select Candidate Target to Inspect",
                options=target_symbols,
                index=selected_idx,
                key="target_selector",
            )
            st.session_state["selected_target"] = chosen_symbol

            target_data = extract_target_detail(state, chosen_symbol)
            ranking_info = target_data["ranking"] or {}

            # Target Profile Banner
            t_col1, t_col2 = st.columns([3, 2])
            with t_col1:
                st.subheader(f"Target: {chosen_symbol}")
                meta = target_data["metadata"]
                st.write(f"**Approved Name**: {meta.get('target_name') or ranking_info.get('target_name') or 'N/A'}")
                st.write(f"**Ensembl ID**: `{meta.get('ensembl_id') or 'Unmapped'}`  |  **Disease Association**: {state.get('disease_name', '')}")
                tier_badge = format_confidence_badge(ranking_info.get("confidence_tier", "medium"))
                st.markdown(f"**Overall Priority Score**: **{ranking_info.get('overall_priority_score', 0):.1f} / 100** ({tier_badge})")

                if ranking_info.get("strengths"):
                    st.markdown("**Key Strengths:**")
                    for s in ranking_info["strengths"]:
                        st.markdown(f"- {s}")

                if ranking_info.get("limitations"):
                    st.markdown("**Scientific Limitations:**")
                    for lim in ranking_info["limitations"]:
                        st.markdown(f"- {lim}")

            with t_col2:
                radar_data = ranking_info.get("radar_data", {})
                if radar_data:
                    fig_radar = render_radar_chart(radar_data, chosen_symbol)
                    if fig_radar:
                        st.plotly_chart(fig_radar, use_container_width=True)

            # Sub-tabs for deep dive modalities
            sub_lit, sub_ot, sub_exp, sub_chem = st.tabs([
                "📚 Literature Evidence",
                "🎯 Open Targets & Tractability",
                "🧪 Experimental Validation",
                "💊 Compound & Bioactivity",
            ])

            with sub_lit:
                target_evs = target_data["evidence"]
                lit_evs = [ev for ev in target_evs if ev.get("source_database") == "PubMed" or "pmid" in (ev.get("citation") or {})]
                if not lit_evs:
                    st.info(f"No specific literature records linked to {chosen_symbol}.")
                else:
                    st.markdown(f"**Found {len(lit_evs)} supporting literature evidence records:**")
                    for ev in lit_evs:
                        cit = ev.get("citation", {})
                        pmid = cit.get("pmid")
                        title = cit.get("title", "Research Article")
                        authors = ", ".join(cit.get("authors", [])) or "Authors unlisted"
                        year = cit.get("publication_year", "")
                        statement = ev.get("extracted_statement") or "Evidence linking target to disease pathology."
                        causality = ev.get("causality_level", "").replace("_", " ").title()

                        st.markdown(
                            f"<div style='border:1px solid #e2e8f0; border-radius:6px; padding:12px; margin-bottom:10px; background-color:#ffffff;'>"
                            f"<div style='font-size:14px; font-weight:600; color:#0f172a;'>{title}</div>"
                            f"<div style='font-size:12px; color:#64748b;'>{authors} ({year}) | <b>Causality Level:</b> {causality}</div>"
                            f"<div style='margin-top:6px; font-size:13px; color:#334155;'><i>\"{statement}\"</i></div>"
                            + (f"<div style='margin-top:6px;'><a href='https://pubmed.ncbi.nlm.nih.gov/{pmid}/' target='_blank'>🔗 View on PubMed (PMID: {pmid})</a></div>" if pmid else "")
                            + "</div>",
                            unsafe_allow_html=True,
                        )

            with sub_ot:
                druggability = target_data["druggability"]
                if not druggability:
                    st.info(f"No Open Targets tractability assessment available for {chosen_symbol}.")
                else:
                    st.metric("Overall Tractability Score", f"{druggability.get('overall_tractability_score', 0):.1f} / 100")
                    st.markdown(f"**Summary Rationale**: {druggability.get('summary_rationale', 'Assessed via Open Targets Platform.')}")

                    modalities = druggability.get("modalities", {})
                    if modalities:
                        st.markdown("#### Modality Precedence Breakdown")
                        mod_rows = []
                        for mod_name, mod_info in modalities.items():
                            mod_rows.append({
                                "Modality": mod_name.replace("_", " ").title(),
                                "Precedence Bucket": mod_info.get("bucket", "").replace("_", " ").title(),
                                "Tractability Score": f"{mod_info.get('score', 0):.1f}",
                                "Details": mod_info.get("details", ""),
                            })
                        st.dataframe(pd.DataFrame(mod_rows), use_container_width=True, hide_index=True)

            with sub_exp:
                exp_records = target_data["experimental"]
                if not exp_records:
                    st.info(f"No internal validation assay records matched for {chosen_symbol}.")
                else:
                    st.info("ℹ️ **Synthetic Assay Disclaimer**: These records originate from demonstration datasets and do not represent proprietary company data.")
                    exp_rows = []
                    for r in exp_records:
                        exp_rows.append({
                            "Assay ID": r.get("record_id"),
                            "Assay Type": r.get("assay_type"),
                            "Model / Cell Line": r.get("cell_line_or_model"),
                            "Measurement": f"{r.get('measurement_name')} = {r.get('measurement_value')} {r.get('measurement_unit')}",
                            "p-value": r.get("p_value") or "N/A",
                            "QC Passed": "✓" if r.get("qc_passed") else "✗",
                        })
                    st.dataframe(pd.DataFrame(exp_rows), use_container_width=True, hide_index=True)

            with sub_chem:
                known = target_data["known_compounds"]
                screened = target_data["simulated_compounds"]

                fig_chem = render_compound_bioactivity_chart(known, screened, chosen_symbol)
                if fig_chem:
                    st.plotly_chart(fig_chem, use_container_width=True)

                c_known, c_sim = st.columns(2)
                with c_known:
                    st.markdown("#### 🔬 ChEMBL Measured Bioactivity")
                    st.caption("Empirically measured binding or functional assays from literature.")
                    if not known:
                        st.write("No measured ChEMBL active molecules returned for this target.")
                    else:
                        known_rows = []
                        for k in known:
                            known_rows.append({
                                "ChEMBL ID": k.get("compound_id"),
                                "Molecule Name": k.get("compound_name") or "Unannotated",
                                "Activity": f"{k.get('activity_type')} = {k.get('activity_value')} {k.get('activity_unit')}",
                                "Assay ID": k.get("assay_chembl_id") or "N/A",
                            })
                        st.dataframe(pd.DataFrame(known_rows), use_container_width=True, hide_index=True)

                with c_sim:
                    st.markdown("#### 💻 In Silico Screening Predictions")
                    st.warning("⚠️ **Disclaimer**: *Computational simulation prediction — not experimentally measured.*")
                    if not screened:
                        st.write("No in silico screening predictions generated.")
                    else:
                        sim_rows = []
                        for s in screened:
                            sim_rows.append({
                                "Compound ID": s.get("compound_id"),
                                "Pred Affinity (kcal/mol)": s.get("predicted_binding_affinity_kcal_mol"),
                                "Est. Kd (nM)": s.get("predicted_kd_nm"),
                                "MW": s.get("molecular_weight"),
                                "LogP": s.get("logp"),
                            })
                        st.dataframe(pd.DataFrame(sim_rows), use_container_width=True, hide_index=True)

    # --- TAB 3: RESEARCH REPORT & EXPORT ---
    with tab_report:
        report_obj = generate_research_report(state)
        report_md = report_to_markdown(report_obj, state=state)
        report_json = report_to_json(report_obj)

        col_dl1, col_dl2 = st.columns([1, 1])
        with col_dl1:
            st.download_button(
                label="📥 Download Scientific Report (Markdown)",
                data=report_md,
                file_name=f"{report_obj.report_id}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_dl2:
            st.download_button(
                label="📥 Download Full State Data (JSON)",
                data=report_json,
                file_name=f"{report_obj.report_id}.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown("---")
        st.markdown(report_md, unsafe_allow_html=True)

    # --- TAB 4: AGENT AUDIT TRACE & OBSERVABILITY ---
    with tab_trace:
        trace = state.get("audit_trace", [])
        if not trace:
            st.info("No audit trace records available.")
        else:
            all_agents = ["All Agents"] + sorted(list(set(t.get("agent_name", "") for t in trace if t.get("agent_name"))))
            filter_choice = st.selectbox("Filter by Agent", options=all_agents, index=0)
            filtered_trace = filter_audit_trace(trace, filter_choice)

            st.markdown(f"**Showing {len(filtered_trace)} execution trace events:**")
            for idx, event in enumerate(filtered_trace, start=1):
                agent_name = event.get("agent_name", "Agent")
                status = event.get("status", "success")
                dur = f"{event.get('duration_ms', 0):.1f}ms"
                status_icon = "🟢" if status == "success" else ("🟡" if status == "degraded" else "🔴")

                with st.expander(f"{status_icon} Step {idx}: {agent_name} ({event.get('stage')}) — {dur}", expanded=(idx == len(filtered_trace))):
                    st.write(f"**Input Summary**: {event.get('input_summary')}")
                    st.write(f"**Output Summary**: {event.get('output_summary')}")
                    if event.get("tool_calls"):
                        st.markdown(f"**Tools Executed**: `{', '.join(event['tool_calls'])}`")
                    if event.get("notes"):
                        st.info(f"**Scientific Note**: {event['notes']}")


if __name__ == "__main__":
    main()
