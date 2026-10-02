import React, { useState, useMemo } from 'react';
import type { EvidenceItem } from '../../types';
import {
  BookOpenCheck,
  Search,
  ExternalLink,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

interface EvidenceExplorerViewProps {
  evidence: EvidenceItem[];
  onSelectTarget?: (symbol: string) => void;
}

export const EvidenceExplorerView: React.FC<EvidenceExplorerViewProps> = ({
  evidence,
  onSelectTarget,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTarget, setSelectedTarget] = useState('ALL');
  const [conflictFilter, setConflictFilter] = useState<'ALL' | 'SUPPORTING' | 'CONTRADICTION'>('ALL');

  const targetSymbols = useMemo(() => {
    const syms = Array.from(new Set(evidence.map((e) => e.target_symbol)));
    return ['ALL', ...syms];
  }, [evidence]);

  const filteredEvidence = useMemo(() => {
    return evidence.filter((item) => {
      if (selectedTarget !== 'ALL' && item.target_symbol !== selectedTarget) return false;
      if (conflictFilter === 'SUPPORTING' && item.is_contradictory) return false;
      if (conflictFilter === 'CONTRADICTION' && !item.is_contradictory) return false;

      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const title = item.citation?.title?.toLowerCase() || '';
        const snippet = item.summary_snippet?.toLowerCase() || '';
        const sym = item.target_symbol.toLowerCase();
        return title.includes(query) || snippet.includes(query) || sym.includes(query);
      }
      return true;
    });
  }, [evidence, selectedTarget, conflictFilter, searchTerm]);

  return (
    <div className="space-y-6">
      {/* Search & Filter Header Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md shadow-xl">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <BookOpenCheck className="h-5 w-5 text-cyan-400" />
            <div>
              <h3 className="text-sm font-bold text-white">Multi-Modal Evidence Explorer</h3>
              <p className="text-xs text-slate-400">
                Explore genetic variants, GWAS loci, preclinical citations, and clinical contradictions.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Target symbol filter */}
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
            >
              {targetSymbols.map((s) => (
                <option key={s} value={s}>
                  {s === 'ALL' ? 'All Targets' : `Target: ${s}`}
                </option>
              ))}
            </select>

            {/* Conflict toggle */}
            <select
              value={conflictFilter}
              onChange={(e) => setConflictFilter(e.target.value as any)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
            >
              <option value="ALL">All Evidence ({evidence.length})</option>
              <option value="SUPPORTING">Supporting Only</option>
              <option value="CONTRADICTION">Contradictions / Risks Only</option>
            </select>

            {/* Keyword search input */}
            <div className="relative flex-1 md:w-60">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search literature text..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950/80 pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Evidence Cards List */}
      <div className="space-y-3">
        {filteredEvidence.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center text-xs text-slate-400">
            No evidence records matched your search filters.
          </div>
        ) : (
          filteredEvidence.map((ev, idx) => {
            const isContradiction = Boolean(ev.is_contradictory);

            return (
              <div
                key={ev.evidence_id || idx}
                className={`rounded-xl border p-4.5 text-xs shadow-md transition-all ${
                  isContradiction
                    ? 'border-rose-900/50 bg-rose-950/20'
                    : 'border-slate-800 bg-slate-900/70 hover:border-slate-700'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800/80 mb-2">
                  <div className="flex items-center gap-2">
                    <span
                      onClick={() => onSelectTarget && onSelectTarget(ev.target_symbol)}
                      className="font-bold text-white bg-slate-800 px-2.5 py-0.5 rounded text-xs tracking-wider cursor-pointer hover:text-cyan-400 transition-colors"
                    >
                      {ev.target_symbol}
                    </span>

                    {isContradiction ? (
                      <span className="flex items-center gap-1 rounded bg-rose-500/20 border border-rose-500/40 px-2 py-0.5 text-[10px] font-bold text-rose-300 uppercase">
                        <AlertTriangle className="h-3 w-3" />
                        Clinical Risk / Contradiction
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 rounded bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-[10px] font-bold text-emerald-300 uppercase">
                        <CheckCircle2 className="h-3 w-3" />
                        Supporting Evidence
                      </span>
                    )}

                    <span className="capitalize text-slate-400 font-mono text-[11px]">
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

                <h4 className="text-sm font-bold text-slate-100 mb-1">
                  {ev.citation?.title || 'Biomedical Evidence Record'}
                </h4>

                {ev.summary_snippet && (
                  <p className="text-slate-300 text-xs leading-relaxed my-2">
                    {ev.summary_snippet}
                  </p>
                )}

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-2 text-[11px] text-slate-400">
                  <div className="flex items-center gap-4">
                    <span>
                      Database: <strong className="text-slate-200">{ev.source_database || 'PubMed'}</strong>
                    </span>
                    {ev.causality_level && (
                      <span className="font-mono">
                        Causality: <span className="text-cyan-300">{ev.causality_level.replace(/_/g, ' ')}</span>
                      </span>
                    )}
                  </div>

                  {ev.confidence_score !== undefined && (
                    <div className="font-mono text-slate-300">
                      Score: <strong className="text-emerald-400">{(ev.confidence_score * 100).toFixed(0)}%</strong>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
