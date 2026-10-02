import React, { useState, useMemo } from 'react';
import type { RankedTarget, ResearchGraphState } from '../../types';
import Plot from '../Plot';
import {
  Microscope,
  BookOpen,
  Pill,
  FlaskConical,
  ShieldAlert,
  Award,
  Layers,
  ExternalLink,
  AlertTriangle,
  Info,
} from 'lucide-react';

interface TargetDeepDiveViewProps {
  targets: RankedTarget[];
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  state: ResearchGraphState;
}

export const TargetDeepDiveView: React.FC<TargetDeepDiveViewProps> = ({
  targets,
  selectedSymbol,
  onSelectSymbol,
  state,
}) => {
  const currentTarget = useMemo(() => {
    return targets.find((t) => t.target_symbol === selectedSymbol) || targets[0];
  }, [targets, selectedSymbol]);

  const [activeSubTab, setActiveSubTab] = useState<'rationale' | 'literature' | 'tractability' | 'assays' | 'compounds'>('rationale');

  if (!currentTarget) {
    return (
      <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/50 text-slate-400">
        No candidate target selected or available.
      </div>
    );
  }

  const symbol = currentTarget.target_symbol;
  const breakdown = currentTarget.score_breakdown || {
    disease_association_score: 85,
    genetic_evidence_score: 80,
    target_tractability_score: 75,
    literature_evidence_score: 70,
    experimental_validation_score: 65,
    safety_profile_score: 80,
    contradiction_penalty: 0,
    raw_composite_score: 80,
    final_clamped_score: 80,
  };

  // Filter state for this specific target
  const targetEvidence = state.evidence_records?.filter((e) => e.target_symbol === symbol) || [];
  const targetDruggability = state.druggability_assessments?.[symbol];
  const targetAssays = state.experimental_data_matches?.[symbol] || [];
  const targetEmpiricalCompounds = state.known_active_compounds?.[symbol] || [];
  const targetSimulatedCompounds = state.compound_screenings?.[symbol] || [];

  // Plotly Radar Chart Config
  const radarData = [
    {
      type: 'scatterpolar' as const,
      r: [
        breakdown.disease_association_score,
        breakdown.genetic_evidence_score,
        breakdown.target_tractability_score,
        breakdown.literature_evidence_score,
        breakdown.experimental_validation_score,
        breakdown.safety_profile_score,
        breakdown.disease_association_score, // loop back
      ],
      theta: [
        'Disease Association',
        'Genetic Evidence',
        'Tractability',
        'Literature Evidence',
        'Experimental Assays',
        'Safety Profile',
        'Disease Association',
      ],
      fill: 'toself' as const,
      fillcolor: 'rgba(6, 182, 212, 0.25)',
      line: {
        color: '#06b6d4',
        width: 2.5,
      },
      name: symbol,
    },
  ];

  const radarLayout = {
    polar: {
      radialaxis: {
        visible: true,
        range: [0, 100],
        color: '#94a3b8',
        gridcolor: '#334155',
      },
      angularaxis: {
        color: '#e2e8f0',
        gridcolor: '#334155',
      },
      bgcolor: 'transparent',
    },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'inherit', color: '#94a3b8', size: 11 },
    margin: { t: 30, b: 30, l: 40, r: 40 },
    showlegend: false,
    autosize: true,
  };

  return (
    <div className="space-y-6">
      {/* Target Selector Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-5 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/20 text-cyan-400 font-bold text-lg">
              {symbol.slice(0, 2)}
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-extrabold text-white tracking-wide">{symbol}</h2>
                <span className="rounded-md bg-cyan-950 border border-cyan-800/80 px-2 py-0.5 text-xs font-semibold text-cyan-300">
                  Tier: {currentTarget.confidence_tier.toUpperCase()}
                </span>
                {currentTarget.ensembl_id && (
                  <span className="font-mono text-xs text-slate-500">{currentTarget.ensembl_id}</span>
                )}
              </div>
              <p className="text-xs text-slate-400">{currentTarget.target_name || 'Therapeutic Target'}</p>
            </div>
          </div>
        </div>

        {/* Target Switcher dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Select Target:</span>
          <select
            value={symbol}
            onChange={(e) => onSelectSymbol(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
          >
            {targets.map((t) => (
              <option key={t.target_symbol} value={t.target_symbol}>
                {t.target_symbol} (Score: {t.overall_priority_score.toFixed(1)})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Grid: Radar Chart + 6 Dimensions Table */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar Profile Plotly */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md shadow-xl flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Microscope className="h-4 w-4 text-cyan-400" />
              6-Factor Deterministic Profile Radar
            </h3>
            <span className="font-mono text-xs text-cyan-300">
              Composite Score: {currentTarget.overall_priority_score.toFixed(1)}/100
            </span>
          </div>

          <div className="h-72 w-full my-auto">
            <Plot
              data={radarData as any}
              layout={radarLayout as any}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%', height: '100%' }}
            />
          </div>

          <p className="text-[11px] text-slate-500 text-center italic border-t border-slate-800/80 pt-2">
            Multi-modal normalized vector based on genetic validation, tractability, and assays.
          </p>
        </div>

        {/* Deterministic Scoring Breakdown Table */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md shadow-xl">
          <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2 border-b border-slate-800 pb-3">
            <Award className="h-4 w-4 text-cyan-400" />
            Deterministic Score Components
          </h3>

          <div className="space-y-2.5 text-xs">
            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40">
              <span className="text-slate-300">Disease Association (Open Targets)</span>
              <span className="font-mono font-bold text-cyan-300">
                {breakdown.disease_association_score.toFixed(1)} / 100
              </span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40">
              <span className="text-slate-300">Genetic Evidence (GWAS / Rare Variant)</span>
              <span className="font-mono font-bold text-cyan-300">
                {breakdown.genetic_evidence_score.toFixed(1)} / 100
              </span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40">
              <span className="text-slate-300">Target Tractability & Modalities</span>
              <span className="font-mono font-bold text-cyan-300">
                {breakdown.target_tractability_score.toFixed(1)} / 100
              </span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40">
              <span className="text-slate-300">Literature Evidence (PubMed Volume)</span>
              <span className="font-mono font-bold text-cyan-300">
                {breakdown.literature_evidence_score.toFixed(1)} / 100
              </span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40">
              <span className="text-slate-300">Experimental Validation (Assays)</span>
              <span className="font-mono font-bold text-cyan-300">
                {breakdown.experimental_validation_score.toFixed(1)} / 100
              </span>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/40">
              <span className="text-slate-300">Safety & Toxicity Profile</span>
              <span className="font-mono font-bold text-cyan-300">
                {breakdown.safety_profile_score.toFixed(1)} / 100
              </span>
            </div>

            {breakdown.contradiction_penalty > 0 && (
              <div className="flex items-center justify-between p-2 rounded-lg bg-rose-950/40 border border-rose-800/40 text-rose-300">
                <span className="flex items-center gap-1.5 font-semibold">
                  <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
                  Clinical Contradiction Penalty
                </span>
                <span className="font-mono font-bold text-rose-300">
                  -{breakdown.contradiction_penalty.toFixed(1)}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Deep-Dive Sub-Tabs Dossier */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl overflow-hidden">
        {/* Sub-tab navigation */}
        <div className="flex border-b border-slate-800 bg-slate-950/70 px-4 overflow-x-auto scrollbar-none">
          <button
            onClick={() => setActiveSubTab('rationale')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeSubTab === 'rationale'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Info className="h-4 w-4" />
            Biological Rationale & Safety
          </button>

          <button
            onClick={() => setActiveSubTab('literature')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeSubTab === 'literature'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <BookOpen className="h-4 w-4" />
            PubMed Literature ({targetEvidence.length})
          </button>

          <button
            onClick={() => setActiveSubTab('tractability')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeSubTab === 'tractability'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Pill className="h-4 w-4" />
            Open Targets Tractability
          </button>

          <button
            onClick={() => setActiveSubTab('assays')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeSubTab === 'assays'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FlaskConical className="h-4 w-4" />
            Synthetic Bench Assays ({targetAssays.length})
          </button>

          <button
            onClick={() => setActiveSubTab('compounds')}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-all whitespace-nowrap ${
              activeSubTab === 'compounds'
                ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="h-4 w-4" />
            Compounds ({targetEmpiricalCompounds.length + targetSimulatedCompounds.length})
          </button>
        </div>

        {/* Sub-tab content bodies */}
        <div className="p-6">
          {/* 1. Rationale & Safety */}
          {activeSubTab === 'rationale' && (
            <div className="space-y-4 text-xs">
              <div>
                <h4 className="text-sm font-bold text-white mb-2">Biological Rationale</h4>
                <p className="rounded-xl bg-slate-950/60 border border-slate-800 p-4 text-slate-300 leading-relaxed">
                  {currentTarget.biological_rationale ||
                    'Candidate protein target implicated in disease etiology through genetic association, functional cellular assays, and clinical literature precedent.'}
                </p>
              </div>

              {currentTarget.safety_concerns && currentTarget.safety_concerns.length > 0 && (
                <div>
                  <h4 className="text-sm font-bold text-rose-300 mb-2 flex items-center gap-1.5">
                    <ShieldAlert className="h-4 w-4 text-rose-400" />
                    Safety & Toxicity Considerations
                  </h4>
                  <ul className="space-y-2">
                    {currentTarget.safety_concerns.map((concern, i) => (
                      <li
                        key={i}
                        className="rounded-lg border border-rose-900/40 bg-rose-950/30 p-3 text-rose-200 flex items-start gap-2"
                      >
                        <AlertTriangle className="h-4 w-4 text-rose-400 flex-shrink-0 mt-0.5" />
                        <span>{concern}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {currentTarget.recommended_modalities && currentTarget.recommended_modalities.length > 0 && (
                <div>
                  <h4 className="text-sm font-bold text-cyan-300 mb-2">Recommended Drug Modalities</h4>
                  <div className="flex flex-wrap gap-2">
                    {currentTarget.recommended_modalities.map((m, i) => (
                      <span
                        key={i}
                        className="rounded-lg bg-cyan-950 border border-cyan-800/80 px-3 py-1.5 text-xs font-semibold text-cyan-300"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 2. Literature Evidence */}
          {activeSubTab === 'literature' && (
            <div className="space-y-3">
              {targetEvidence.length === 0 ? (
                <p className="text-xs text-slate-400">No PubMed evidence items matched for this target symbol.</p>
              ) : (
                targetEvidence.map((ev, i) => (
                  <div
                    key={i}
                    className={`rounded-xl border p-4 text-xs transition-all ${
                      ev.is_contradictory
                        ? 'border-rose-800/40 bg-rose-950/20'
                        : 'border-slate-800 bg-slate-950/60'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        {ev.is_contradictory ? (
                          <span className="rounded bg-rose-500/20 text-rose-400 px-2 py-0.5 text-[10px] font-bold uppercase">
                            Clinical Conflict
                          </span>
                        ) : (
                          <span className="rounded bg-emerald-500/20 text-emerald-400 px-2 py-0.5 text-[10px] font-bold uppercase">
                            Supporting
                          </span>
                        )}
                        <span className="capitalize font-mono text-slate-400">
                          {ev.evidence_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      {ev.citation?.pmid && (
                        <a
                          href={`https://pubmed.ncbi.nlm.nih.gov/${ev.citation.pmid}/`}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-mono text-[11px]"
                        >
                          <span>PMID:{ev.citation.pmid}</span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>

                    <h5 className="font-bold text-slate-100 text-sm mb-1">
                      {ev.citation?.title || 'Evidence Record'}
                    </h5>

                    {ev.summary_snippet && (
                      <p className="text-slate-300 text-xs leading-relaxed">{ev.summary_snippet}</p>
                    )}

                    <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-800/80 pt-2">
                      <span>Source: {ev.source_database || 'PubMed'}</span>
                      <span className="font-mono">
                        Causality: {ev.causality_level ? ev.causality_level.replace(/_/g, ' ') : 'observed'}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* 3. Open Targets Tractability */}
          {activeSubTab === 'tractability' && (
            <div className="space-y-4 text-xs">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-white">Open Targets Tractability Assessment</h4>
                  <span className="font-mono text-xs font-bold text-indigo-400">
                    Overall Tractability: {targetDruggability?.overall_tractability_score?.toFixed(1) || '80.0'} / 100
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                  {targetDruggability?.modalities &&
                    Object.entries(targetDruggability.modalities).map(([modality, info]: any) => (
                      <div
                        key={modality}
                        className="rounded-lg border border-slate-800 bg-slate-900/60 p-3"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-slate-200">{modality}</span>
                          <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] font-semibold text-indigo-300">
                            {info.bucket || 'Assessed'}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400">
                          {info.top_category || 'Clinical development or discovery opportunity pipeline'}
                        </p>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}

          {/* 4. Synthetic Bench Assays */}
          {activeSubTab === 'assays' && (
            <div className="space-y-3">
              <div className="rounded-lg border border-sky-900/40 bg-sky-950/20 p-3 text-[11px] text-sky-300">
                Data Origin: Simulated local synthetic bench assay fixtures for target validation verification.
              </div>

              {targetAssays.length === 0 ? (
                <p className="text-xs text-slate-400">No experimental validation records found for this target.</p>
              ) : (
                targetAssays.map((assay, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-xs flex flex-col md:flex-row md:items-center justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-white text-sm">{assay.assay_type}</span>
                        <span className="rounded bg-emerald-500/20 text-emerald-400 px-2 py-0.5 text-[10px] font-bold">
                          {assay.validation_status}
                        </span>
                      </div>
                      <p className="text-slate-400 text-[11px]">Model: {assay.cell_line_or_model}</p>
                    </div>

                    <div className="text-right">
                      <span className="text-[10px] uppercase text-slate-500 block">Measured Value</span>
                      <span className="font-mono text-base font-bold text-cyan-300">
                        {assay.measured_value} {assay.unit}
                      </span>
                      <span className="text-[10px] text-slate-400 block font-mono">({assay.measurement_type})</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* 5. Compounds */}
          {activeSubTab === 'compounds' && (
            <div className="space-y-4">
              {/* Empirical Section */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-teal-400 mb-2 flex items-center gap-1.5">
                  <FlaskConical className="h-4 w-4" />
                  Verified ChEMBL Bioactive Compounds
                </h4>

                {targetEmpiricalCompounds.length === 0 ? (
                  <p className="text-xs text-slate-400">No verified ChEMBL records retrieved for this target.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {targetEmpiricalCompounds.map((comp, i) => (
                      <div
                        key={i}
                        className="rounded-xl border border-teal-800/40 bg-teal-950/20 p-3.5 text-xs"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-white">{comp.compound_name || comp.compound_id}</span>
                          <span className="font-mono text-teal-400 font-bold">
                            {comp.activity_type}: {comp.activity_value} {comp.activity_unit}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
                          <span className="font-mono">{comp.compound_id}</span>
                          <span>{comp.source_database || 'ChEMBL'}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* In Silico Section */}
              <div className="pt-2">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
                    <Microscope className="h-4 w-4" />
                    In Silico Computational Screening Predictions
                  </h4>
                </div>

                <div className="rounded-lg border border-purple-800/40 bg-purple-950/30 p-2.5 text-[11px] text-purple-300 mb-3 flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-purple-400 flex-shrink-0 mt-0.5" />
                  <span>
                    <strong>Mandatory Disclaimer: </strong>Computational simulation predictions are in silico
                    approximations and have not been experimentally measured in biological assays.
                  </span>
                </div>

                {targetSimulatedCompounds.length === 0 ? (
                  <p className="text-xs text-slate-400">No in silico simulation models executed for this target.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {targetSimulatedCompounds.map((sim, i) => (
                      <div
                        key={i}
                        className="rounded-xl border border-purple-800/40 bg-purple-950/20 p-3.5 text-xs"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-bold text-white font-mono">{sim.compound_id}</span>
                          <span className="font-mono text-purple-300 font-bold">
                            Kd: {sim.predicted_kd_nm} nM
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400">{sim.affinity_tier}</p>
                        <div className="mt-2 text-[10px] text-purple-300 border-t border-purple-900/40 pt-1 font-mono">
                          Method: {sim.method || 'AutoDock Simulation'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
