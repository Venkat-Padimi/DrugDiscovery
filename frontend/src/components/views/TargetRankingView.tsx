import React, { useState, useMemo } from 'react';
import type { RankedTarget } from '../../types';
import {
  ListOrdered,
  Search,
  ArrowUpDown,
  ChevronRight,
} from 'lucide-react';

interface TargetRankingViewProps {
  targets: RankedTarget[];
  onSelectTarget: (symbol: string) => void;
}

export const TargetRankingView: React.FC<TargetRankingViewProps> = ({ targets, onSelectTarget }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<'overall_priority_score' | 'target_symbol' | 'evidence_count'>('overall_priority_score');
  const [sortAsc, setSortAsc] = useState(false);

  const filteredTargets = useMemo(() => {
    return targets
      .filter((t) => {
        const query = searchTerm.toLowerCase();
        return (
          t.target_symbol.toLowerCase().includes(query) ||
          (t.target_name && t.target_name.toLowerCase().includes(query)) ||
          (t.tractability_summary && t.tractability_summary.toLowerCase().includes(query))
        );
      })
      .sort((a, b) => {
        let valA = a[sortField] || 0;
        let valB = b[sortField] || 0;
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        if (valA < valB) return sortAsc ? -1 : 1;
        if (valA > valB) return sortAsc ? 1 : -1;
        return 0;
      });
  }, [targets, searchTerm, sortField, sortAsc]);

  const handleSort = (field: 'overall_priority_score' | 'target_symbol' | 'evidence_count') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const highTierCount = targets.filter((t) => t.confidence_tier?.toLowerCase() === 'high').length;
  const medTierCount = targets.filter((t) => t.confidence_tier?.toLowerCase() === 'medium').length;
  const lowTierCount = targets.filter((t) => t.confidence_tier?.toLowerCase() === 'low').length;

  return (
    <div className="space-y-6">
      {/* Overview Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">Total Ranked Candidates</div>
          <div className="mt-1 font-mono text-2xl font-bold text-white">{targets.length}</div>
        </div>
        <div className="rounded-xl border border-emerald-900/40 bg-emerald-950/20 p-4">
          <div className="text-xs font-medium text-emerald-400">High Confidence</div>
          <div className="mt-1 font-mono text-2xl font-bold text-emerald-300">{highTierCount}</div>
        </div>
        <div className="rounded-xl border border-sky-900/40 bg-sky-950/20 p-4">
          <div className="text-xs font-medium text-sky-400">Medium Confidence</div>
          <div className="mt-1 font-mono text-2xl font-bold text-sky-300">{medTierCount}</div>
        </div>
        <div className="rounded-xl border border-amber-900/40 bg-amber-950/20 p-4">
          <div className="text-xs font-medium text-amber-400">Low / Emerging</div>
          <div className="mt-1 font-mono text-2xl font-bold text-amber-300">{lowTierCount}</div>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl overflow-hidden">
        {/* Table Header Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <ListOrdered className="h-5 w-5 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">Prioritized Therapeutic Targets</h3>
            <span className="text-xs text-slate-400">({filteredTargets.length} candidates)</span>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by symbol or name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
          </div>
        </div>

        {/* Dense Scientific Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="border-b border-slate-800 bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400">
              <tr>
                <th className="py-3 px-4 font-semibold">Rank</th>
                <th
                  onClick={() => handleSort('target_symbol')}
                  className="py-3 px-4 font-semibold cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1">
                    <span>Target Symbol</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </div>
                </th>
                <th className="py-3 px-4 font-semibold">Target Name</th>
                <th
                  onClick={() => handleSort('overall_priority_score')}
                  className="py-3 px-4 font-semibold cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1">
                    <span>Priority Score</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </div>
                </th>
                <th className="py-3 px-4 font-semibold">Confidence Tier</th>
                <th className="py-3 px-4 font-semibold">Tractability</th>
                <th className="py-3 px-4 font-semibold">Experimental Validation</th>
                <th
                  onClick={() => handleSort('evidence_count')}
                  className="py-3 px-4 font-semibold cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1">
                    <span>Evidence</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </div>
                </th>
                <th className="py-3 px-4 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredTargets.map((target, idx) => {
                const tier = target.confidence_tier?.toLowerCase();
                const tierBadge =
                  tier === 'high'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : tier === 'medium'
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                    : 'bg-amber-500/20 text-amber-400 border border-amber-500/30';

                return (
                  <tr
                    key={target.target_symbol}
                    className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                    onClick={() => onSelectTarget(target.target_symbol)}
                  >
                    <td className="py-3 px-4 font-mono font-bold text-slate-400">
                      #{idx + 1}
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-bold text-white tracking-wide group-hover:text-cyan-300">
                        {target.target_symbol}
                      </div>
                      {target.ensembl_id && (
                        <div className="font-mono text-[10px] text-slate-500">{target.ensembl_id}</div>
                      )}
                    </td>

                    <td className="py-3 px-4 max-w-[200px] truncate text-slate-300">
                      {target.target_name || 'N/A'}
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-extrabold text-cyan-300">
                          {target.overall_priority_score.toFixed(1)}
                        </span>
                        <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500"
                            style={{ width: `${Math.min(100, target.overall_priority_score)}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${tierBadge}`}>
                        {target.confidence_tier}
                      </span>
                    </td>

                    <td className="py-3 px-4 max-w-[180px] truncate text-slate-300">
                      {target.tractability_summary || 'Unassessed'}
                    </td>

                    <td className="py-3 px-4 max-w-[180px] truncate text-slate-300">
                      {target.experimental_validation_status || 'Unassayed'}
                    </td>

                    <td className="py-3 px-4 font-mono text-center font-bold text-slate-400">
                      {target.evidence_count || 0}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectTarget(target.target_symbol);
                        }}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-medium text-cyan-400 hover:border-cyan-500 hover:bg-slate-700 transition-colors"
                      >
                        <span>Dossier</span>
                        <ChevronRight className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
