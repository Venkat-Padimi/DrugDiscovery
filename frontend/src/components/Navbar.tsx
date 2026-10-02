import React from 'react';
import {
  Dna,
  Network,
  ListOrdered,
  Microscope,
  FlaskConical,
  BookOpenCheck,
  FileText,
  Activity,
  Layers,
  Sparkles,
} from 'lucide-react';

export type ActiveTab =
  | 'workspace'
  | 'graph'
  | 'ranking'
  | 'deepdive'
  | 'screening'
  | 'evidence'
  | 'report'
  | 'trace';

interface NavbarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  sessionId: string;
  diseaseName: string;
  isBackendHealthy: boolean;
  onLoadDemo: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  sessionId,
  diseaseName,
  isBackendHealthy,
  onLoadDemo,
}) => {
  const tabs = [
    { id: 'workspace' as ActiveTab, label: 'Workspace', icon: Layers },
    { id: 'graph' as ActiveTab, label: 'Discovery Graph', icon: Network },
    { id: 'ranking' as ActiveTab, label: 'Target Ranking', icon: ListOrdered },
    { id: 'deepdive' as ActiveTab, label: 'Target Deep Dive', icon: Microscope },
    { id: 'screening' as ActiveTab, label: 'Compound Screening', icon: FlaskConical },
    { id: 'evidence' as ActiveTab, label: 'Evidence Explorer', icon: BookOpenCheck },
    { id: 'report' as ActiveTab, label: 'Research Report', icon: FileText },
    { id: 'trace' as ActiveTab, label: 'Audit Trace', icon: Activity },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/20">
            <Dna className="h-6 w-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-white text-base sm:text-lg">
                Biomedical Target Workbench
              </span>
              <span className="rounded bg-cyan-950 border border-cyan-800/60 px-1.5 py-0.2 text-[10px] font-mono text-cyan-400">
                v0.1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Autonomous Agentic AI Platform for Target Prioritization & Bioactivity
            </p>
          </div>
        </div>

        {/* Active Session & Status Info */}
        <div className="hidden lg:flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-400">Target:</span>
            <span className="font-semibold text-slate-200 truncate max-w-[180px]">{diseaseName || 'Unassigned'}</span>
          </div>

          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-xs font-mono">
            <span className="text-slate-400">Session:</span>
            <span className="text-cyan-400">{sessionId}</span>
          </div>

          <div className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1.5 text-xs">
            <span className={`h-2 w-2 rounded-full ${isBackendHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
            <span className="text-slate-400 font-mono text-[11px]">
              {isBackendHealthy ? 'API Online' : 'Standalone'}
            </span>
          </div>

          <button
            onClick={onLoadDemo}
            className="flex items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-cyan-950/40 px-2.5 py-1.5 text-xs font-medium text-cyan-300 hover:bg-cyan-900/40 hover:border-cyan-400 transition-colors"
            title="Load curated Alzheimer study benchmark"
          >
            <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
            <span>Load Demo Study</span>
          </button>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="border-t border-slate-800/60 bg-slate-950/50 backdrop-blur-lg px-4 sm:px-6">
        <div className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto py-1 scrollbar-none">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 whitespace-nowrap rounded-md px-3.5 py-2 text-xs font-medium transition-all ${
                  isActive
                    ? 'border border-cyan-500/50 bg-cyan-950/60 text-cyan-300 shadow-sm shadow-cyan-500/10'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
