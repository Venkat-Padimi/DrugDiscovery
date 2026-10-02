import { useState, useEffect, useMemo } from 'react';
import { Navbar } from './components/Navbar';
import type { ActiveTab } from './components/Navbar';
import { WorkspaceView } from './components/views/WorkspaceView';
import { TargetGraphView } from './components/views/TargetGraphView';
import { TargetRankingView } from './components/views/TargetRankingView';
import { TargetDeepDiveView } from './components/views/TargetDeepDiveView';
import { CompoundScreeningView } from './components/views/CompoundScreeningView';
import { EvidenceExplorerView } from './components/views/EvidenceExplorerView';
import { ReportView } from './components/views/ReportView';
import { AuditTraceView } from './components/views/AuditTraceView';

import type { ResearchGraphState, DiscoveryGraphData } from './types';
import { DEMO_INVESTIGATION_STATE } from './services/demoData';
import { checkHealth, getPresets, runInvestigation } from './services/api';
import { stateToDiscoveryGraph } from './services/graphTransformer';
import { AlertCircle, Dna } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('workspace');
  const [state, setState] = useState<ResearchGraphState>(DEMO_INVESTIGATION_STATE);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('TREM2');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [presets, setPresets] = useState<Record<string, { question: string; disease_name: string }>>({
    "Alzheimer's Disease (TREM2 & BACE1)": {
      question: "Identify promising therapeutic targets for Alzheimer's disease.",
      disease_name: "Alzheimer's disease",
    },
    "Parkinson's Disease (SNCA & LRRK2)": {
      question: "Identify high-confidence therapeutic targets for Parkinson's disease.",
      disease_name: "Parkinson's disease",
    },
    "Amyotrophic Lateral Sclerosis (SOD1 & TARDBP)": {
      question: "Prioritize candidate therapeutic targets for Amyotrophic lateral sclerosis.",
      disease_name: "Amyotrophic lateral sclerosis",
    },
  });

  // Calculate or fetch Discovery Graph
  const graphData: DiscoveryGraphData = useMemo(() => {
    return stateToDiscoveryGraph(state, 6);
  }, [state]);

  // Initial mount health check & presets load
  useEffect(() => {
    async function init() {
      try {
        const health = await checkHealth();
        setIsBackendHealthy(health.status === 'healthy');
        const p = await getPresets();
        if (p && Object.keys(p).length > 0) {
          setPresets(p);
        }
      } catch (err) {
        console.warn('Initial setup backend check failed, using fallback preset data:', err);
      }
    }
    init();
  }, []);

  const handleRunInvestigation = async (params: {
    question: string;
    diseaseName: string;
    enableScreening: boolean;
    topN: number;
    maxLit: number;
    weights: Record<string, number>;
  }) => {
    setIsRunning(true);
    setErrorMessage(null);

    try {
      const resultState = await runInvestigation({
        research_question: params.question,
        disease_name: params.diseaseName || undefined,
        enable_compound_screening: params.enableScreening,
        top_n_targets_to_screen: params.topN,
        max_literature_results: params.maxLit,
        scoring_weights: params.weights,
      });

      setState(resultState);
      const topTarget = resultState.target_rankings?.[0]?.target_symbol || 'TREM2';
      setSelectedSymbol(topTarget);

      // Auto-transition to Target Ranking or Discovery Graph
      setActiveTab('ranking');
    } catch (err: any) {
      console.error('Investigation error:', err);
      setErrorMessage(err.message || 'Workflow execution error');
    } finally {
      setIsRunning(false);
    }
  };

  const handleSelectTarget = (symbol: string) => {
    setSelectedSymbol(symbol);
    setActiveTab('deepdive');
  };

  const handleLoadDemo = () => {
    setState(DEMO_INVESTIGATION_STATE);
    setSelectedSymbol('TREM2');
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-slate-950">
      {/* Platform Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        sessionId={state.session_id}
        diseaseName={state.disease_name}
        isBackendHealthy={isBackendHealthy}
        onLoadDemo={handleLoadDemo}
      />

      {/* Main Container */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 py-6">
        {errorMessage && (
          <div className="mb-6 rounded-xl border border-rose-800 bg-rose-950/50 p-4 text-xs text-rose-200 flex items-start gap-3 backdrop-blur-md">
            <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
            <div>
              <strong className="block text-rose-100 text-sm mb-0.5">Workflow Execution Warning</strong>
              <span>{errorMessage}</span>
            </div>
          </div>
        )}

        {/* View Switcher */}
        {activeTab === 'workspace' && (
          <WorkspaceView
            state={state}
            isRunning={isRunning}
            onRunInvestigation={handleRunInvestigation}
            presets={presets}
          />
        )}

        {activeTab === 'graph' && (
          <TargetGraphView graphData={graphData} onSelectTarget={handleSelectTarget} />
        )}

        {activeTab === 'ranking' && (
          <TargetRankingView
            targets={state.target_rankings || []}
            onSelectTarget={handleSelectTarget}
          />
        )}

        {activeTab === 'deepdive' && (
          <TargetDeepDiveView
            targets={state.target_rankings || []}
            selectedSymbol={selectedSymbol}
            onSelectSymbol={setSelectedSymbol}
            state={state}
          />
        )}

        {activeTab === 'screening' && <CompoundScreeningView state={state} />}

        {activeTab === 'evidence' && (
          <EvidenceExplorerView
            evidence={state.evidence_records || []}
            onSelectTarget={handleSelectTarget}
          />
        )}

        {activeTab === 'report' && <ReportView state={state} />}

        {activeTab === 'trace' && <AuditTraceView trace={state.audit_trace || []} />}
      </main>

      {/* Scientific Platform Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/90 py-5 text-center text-xs text-slate-500">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-slate-400">
            <Dna className="h-4 w-4 text-cyan-400" />
            <span>Biomedical Target Discovery Workbench &mdash; Enterprise AI Platform</span>
          </div>

          <div className="text-[11px] text-slate-500">
            NCBI PubMed &bull; Open Targets Platform &bull; ChEMBL &bull; Deterministic 6-Factor Prioritization
          </div>

          <div className="text-[11px] font-mono text-slate-500">
            Status:{' '}
            <span className={isBackendHealthy ? 'text-emerald-400' : 'text-amber-400'}>
              {isBackendHealthy ? 'Connected to FastAPI' : 'Offline / Standalone Mode'}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
