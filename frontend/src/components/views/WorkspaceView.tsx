import React, { useState } from 'react';
import {
  Search,
  Sliders,
  Play,
  RotateCw,
  CheckCircle2,
  Layers,
  FlaskConical,
  BookOpen,
  Target,
  Shield,
  FileCheck,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { ResearchGraphState } from '../../types';

interface WorkspaceViewProps {
  state: ResearchGraphState;
  isRunning: boolean;
  onRunInvestigation: (params: {
    question: string;
    diseaseName: string;
    enableScreening: boolean;
    topN: number;
    maxLit: number;
    weights: Record<string, number>;
  }) => Promise<void>;
  presets: Record<string, { question: string; disease_name: string }>;
}

export const WorkspaceView: React.FC<WorkspaceViewProps> = ({
  state,
  isRunning,
  onRunInvestigation,
  presets,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<string>("Alzheimer's Disease (TREM2 & BACE1)");
  const [question, setQuestion] = useState<string>(state.research_question || '');
  const [diseaseName, setDiseaseName] = useState<string>(state.disease_name || '');
  const [enableScreening, setEnableScreening] = useState<boolean>(true);
  const [topN, setTopN] = useState<number>(5);
  const [maxLit, setMaxLit] = useState<number>(15);
  const [showWeights, setShowWeights] = useState<boolean>(false);

  const [weights, setWeights] = useState<Record<string, number>>({
    disease_association: 0.25,
    genetic_evidence: 0.20,
    target_tractability: 0.20,
    literature_evidence: 0.15,
    experimental_validation: 0.10,
    safety_profile: 0.10,
  });

  const handlePresetSelect = (presetKey: string) => {
    setSelectedPreset(presetKey);
    const p = presets[presetKey];
    if (p) {
      setQuestion(p.question);
      setDiseaseName(p.disease_name);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    onRunInvestigation({
      question: question.trim(),
      diseaseName: diseaseName.trim(),
      enableScreening,
      topN,
      maxLit,
      weights,
    });
  };

  const stages = [
    { id: 'supervisor_plan', label: '1. Plan', icon: Layers },
    { id: 'literature_search', label: '2. Literature', icon: BookOpen },
    { id: 'target_identification', label: '3. Target ID', icon: Target },
    { id: 'evidence_evaluation', label: '4. Evidence', icon: Shield },
    { id: 'druggability_assessment', label: '5. Tractability', icon: Sliders },
    { id: 'compound_screening', label: '6. Screening', icon: FlaskConical },
    { id: 'target_ranking', label: '7. Ranking', icon: Sliders },
    { id: 'supervisor_synthesis', label: '8. Synthesis', icon: FileCheck },
  ];

  const currentStageIndex = stages.findIndex((s) => s.id === state.current_stage);

  return (
    <div className="space-y-6">
      {/* Top Banner / Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="text-xs font-medium text-slate-400">Prioritized Targets</div>
          <div className="mt-1 font-mono text-2xl font-bold text-cyan-400">
            {state.target_rankings?.length || 0}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Multi-modal evaluated</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="text-xs font-medium text-slate-400">PubMed Evidence</div>
          <div className="mt-1 font-mono text-2xl font-bold text-sky-400">
            {state.evidence_records?.length || 0}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Peer-reviewed links</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="text-xs font-medium text-slate-400">Empirical / Screened Compounds</div>
          <div className="mt-1 font-mono text-2xl font-bold text-teal-400">
            {Object.values(state.known_active_compounds || {}).flat().length +
              Object.values(state.compound_screenings || {}).flat().length}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">ChEMBL + In Silico</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
          <div className="text-xs font-medium text-slate-400">Agent Trace Events</div>
          <div className="mt-1 font-mono text-2xl font-bold text-indigo-400">
            {state.audit_trace?.length || 0}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Audit log records</div>
        </div>
      </div>

      {/* Main Investigation Launcher Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md shadow-xl">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Search className="h-5 w-5 text-cyan-400" />
              Autonomous Target Investigation Setup
            </h2>
            <p className="text-xs text-slate-400">
              Formulate a biomedical inquiry or select a preset pathology to orchestrate multi-agent target discovery.
            </p>
          </div>

          {/* Preset Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Preset:</span>
            <select
              value={selectedPreset}
              onChange={(e) => handlePresetSelect(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
            >
              {Object.keys(presets).map((key) => (
                <option key={key} value={key}>
                  {key}
                </option>
              ))}
            </select>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Biomedical Research Question / Therapeutic Hypothesis
            </label>
            <textarea
              rows={2}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Identify promising therapeutic targets for Alzheimer's disease."
              className="w-full rounded-xl border border-slate-700 bg-slate-950/70 p-3 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Target Pathology / Disease Name
              </label>
              <input
                type="text"
                value={diseaseName}
                onChange={(e) => setDiseaseName(e.target.value)}
                placeholder="Alzheimer's disease"
                className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Max Literature Papers: <span className="font-mono text-cyan-400">{maxLit}</span>
              </label>
              <input
                type="range"
                min={5}
                max={30}
                step={5}
                value={maxLit}
                onChange={(e) => setMaxLit(Number(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Screening Candidates: <span className="font-mono text-cyan-400">{topN}</span>
              </label>
              <input
                type="range"
                min={1}
                max={10}
                step={1}
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="w-full accent-cyan-500"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
              <input
                type="checkbox"
                checked={enableScreening}
                onChange={(e) => setEnableScreening(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500"
              />
              <span>Enable Compound Screening & Bioactivity Simulation Stage</span>
            </label>

            <button
              type="button"
              onClick={() => setShowWeights(!showWeights)}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-cyan-400"
            >
              <span>Deterministic Weights ({showWeights ? 'Hide' : 'Customize'})</span>
              {showWeights ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
          </div>

          {/* Collapsible custom weights */}
          {showWeights && (
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
              <div className="text-xs font-semibold text-slate-300">
                6-Factor Deterministic Composite Weights (Normalized to 1.0)
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(weights).map(([k, v]) => (
                  <div key={k} className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-400">
                      <span className="capitalize">{k.replace(/_/g, ' ')}</span>
                      <span className="font-mono text-cyan-400">{v.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min={0.05}
                      max={0.5}
                      step={0.05}
                      value={v}
                      onChange={(e) => setWeights({ ...weights, [k]: parseFloat(e.target.value) })}
                      className="w-full accent-cyan-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Submit Action */}
          <div className="pt-2">
            <button
              type="submit"
              disabled={isRunning || !question.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-cyan-600/20 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 transition-all cursor-pointer"
            >
              {isRunning ? (
                <>
                  <RotateCw className="h-4 w-4 animate-spin text-white" />
                  <span>Executing Multi-Agent Investigation...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-white" />
                  <span>Launch Research Investigation</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* 8-Stage Execution Stepper */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-md">
        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
          <RotateCw className="h-4 w-4 text-cyan-400" />
          LangGraph Multi-Agent Workflow Pipeline
        </h3>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
          {stages.map((stg, idx) => {
            const Icon = stg.icon;
            const isCompleted = state.status === 'completed' || idx < currentStageIndex;
            const isCurrent = isRunning && idx === currentStageIndex;

            return (
              <div
                key={stg.id}
                className={`flex flex-col items-center justify-center rounded-xl border p-3 text-center transition-all ${
                  isCurrent
                    ? 'border-cyan-400 bg-cyan-950/60 text-cyan-300 ring-1 ring-cyan-400 animate-pulse'
                    : isCompleted
                    ? 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300'
                    : 'border-slate-800 bg-slate-900/40 text-slate-500'
                }`}
              >
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-lg mb-1.5 ${
                    isCurrent
                      ? 'bg-cyan-500/20 text-cyan-300'
                      : isCompleted
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : isCurrent ? (
                    <RotateCw className="h-4 w-4 animate-spin text-cyan-300" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                <div className="text-[11px] font-semibold leading-tight">{stg.label}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
