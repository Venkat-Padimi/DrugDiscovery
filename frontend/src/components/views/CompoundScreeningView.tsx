import React, { useState, useMemo } from 'react';
import type { ResearchGraphState } from '../../types';
import Plot from '../Plot';
import {
  AlertTriangle,
  Filter,
  CheckCircle2,
  Layers,
} from 'lucide-react';

interface CompoundScreeningViewProps {
  state: ResearchGraphState;
}

export const CompoundScreeningView: React.FC<CompoundScreeningViewProps> = ({ state }) => {
  const [filterMode, setFilterMode] = useState<'all' | 'empirical' | 'simulated'>('all');

  const empiricalList = useMemo(() => {
    return Object.entries(state.known_active_compounds || {}).flatMap(([target, comps]) =>
      comps.map((c) => ({ ...c, target_symbol: target, is_empirical: true }))
    );
  }, [state.known_active_compounds]);

  const simulatedList = useMemo(() => {
    return Object.entries(state.compound_screenings || {}).flatMap(([target, sims]) =>
      sims.map((s) => ({ ...s, target_symbol: target, is_empirical: false }))
    );
  }, [state.compound_screenings]);

  // Combined Plotly Affinity Chart
  const chartData = useMemo(() => {
    const traces: any[] = [];

    if (filterMode === 'all' || filterMode === 'empirical') {
      traces.push({
        x: empiricalList.map((c) => `${c.target_symbol}: ${c.compound_name || c.compound_id}`),
        y: empiricalList.map((c) => c.activity_value),
        name: 'Empirical Bioactivity (ChEMBL)',
        type: 'bar',
        marker: { color: '#14b8a6' },
      });
    }

    if (filterMode === 'all' || filterMode === 'simulated') {
      traces.push({
        x: simulatedList.map((s) => `${s.target_symbol}: ${s.compound_id}`),
        y: simulatedList.map((s) => s.predicted_kd_nm),
        name: 'In Silico Predicted Kd',
        type: 'bar',
        marker: { color: '#a855f7' },
      });
    }

    return traces;
  }, [empiricalList, simulatedList, filterMode]);

  const chartLayout = {
    title: {
      text: 'Compound Bioactivity & Simulation Profile (nM)',
      font: { color: '#e2e8f0', size: 14 },
    },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'inherit', color: '#94a3b8', size: 11 },
    xaxis: {
      tickangle: -30,
      gridcolor: '#334155',
      color: '#94a3b8',
    },
    yaxis: {
      title: { text: 'Concentration / Kd (nM)' },
      type: 'log' as const,
      gridcolor: '#334155',
      color: '#94a3b8',
    },
    barmode: 'group' as const,
    legend: {
      font: { color: '#e2e8f0' },
      orientation: 'h' as const,
      y: 1.15,
    },
    margin: { t: 50, b: 80, l: 60, r: 20 },
    autosize: true,
  };

  return (
    <div className="space-y-6">
      {/* Prominent Disclaimer Banner */}
      <div className="rounded-xl border border-purple-800/60 bg-purple-950/40 p-4 shadow-lg backdrop-blur-md">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-purple-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-purple-200">
            <span className="font-bold text-sm block text-purple-100 mb-0.5">
              Scientific Bioactivity Disclaimer
            </span>
            Verified ChEMBL measurements are published empirical assay records. All docking scores and predicted Kd
            values labeled as <em>In Silico</em> represent computational simulation models and are{' '}
            <strong>never to be interpreted as experimentally validated bioactivities</strong>.
          </div>
        </div>
      </div>

      {/* Filter Mode Buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Screening Modality:</span>
          <div className="flex rounded-lg border border-slate-800 bg-slate-900/60 p-1">
            <button
              onClick={() => setFilterMode('all')}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
                filterMode === 'all'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              All Molecules ({empiricalList.length + simulatedList.length})
            </button>
            <button
              onClick={() => setFilterMode('empirical')}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
                filterMode === 'empirical'
                  ? 'bg-teal-950 text-teal-300 border border-teal-800'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              ChEMBL Empirical ({empiricalList.length})
            </button>
            <button
              onClick={() => setFilterMode('simulated')}
              className={`rounded-md px-3 py-1 text-xs font-medium transition-all ${
                filterMode === 'simulated'
                  ? 'bg-purple-950 text-purple-300 border border-purple-800'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              In Silico Simulated ({simulatedList.length})
            </button>
          </div>
        </div>
      </div>

      {/* Plotly Chart Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md shadow-xl">
        <div className="h-80 w-full">
          <Plot
            data={chartData}
            layout={chartLayout as any}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: '100%' }}
          />
        </div>
      </div>

      {/* Detailed Compound Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="h-4 w-4 text-cyan-400" />
            Molecular Records & Screening Outputs
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400">
              <tr>
                <th className="py-3 px-4 font-semibold">Target</th>
                <th className="py-3 px-4 font-semibold">Compound / Identifier</th>
                <th className="py-3 px-4 font-semibold">Classification</th>
                <th className="py-3 px-4 font-semibold">Bioactivity / Metric</th>
                <th className="py-3 px-4 font-semibold">Source / Method</th>
                <th className="py-3 px-4 font-semibold">Validation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {(filterMode === 'all' || filterMode === 'empirical') &&
                empiricalList.map((c, idx) => (
                  <tr key={`emp-${idx}`} className="hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-bold text-white">{c.target_symbol}</td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-100">{c.compound_name || c.compound_id}</div>
                      <div className="font-mono text-[10px] text-slate-500">{c.compound_id}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="rounded-md bg-teal-500/20 text-teal-300 border border-teal-500/30 px-2 py-0.5 text-[10px] font-bold uppercase">
                        ChEMBL Empirical
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-teal-300">
                      {c.activity_type}: {c.activity_value} {c.activity_unit}
                    </td>
                    <td className="py-3 px-4 text-slate-400">{c.source_database || 'ChEMBL Database'}</td>
                    <td className="py-3 px-4 text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>Empirically Measured</span>
                    </td>
                  </tr>
                ))}

              {(filterMode === 'all' || filterMode === 'simulated') &&
                simulatedList.map((s, idx) => (
                  <tr key={`sim-${idx}`} className="hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-bold text-white">{s.target_symbol}</td>
                    <td className="py-3 px-4">
                      <div className="font-mono font-bold text-purple-300">{s.compound_id}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="rounded-md bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 text-[10px] font-bold uppercase">
                        In Silico Simulated
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-purple-300">
                      Kd: {s.predicted_kd_nm} nM
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                      {s.method || 'AutoDock Simulation'}
                    </td>
                    <td className="py-3 px-4 text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>Computational Prediction Only</span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
