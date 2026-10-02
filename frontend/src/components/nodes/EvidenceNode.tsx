import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { BookOpen, AlertTriangle } from 'lucide-react';
import type { GraphNodeData } from '../../types';

export const EvidenceNode: React.FC<{ data: GraphNodeData }> = ({ data }) => {
  const isContradictory = Boolean(data.is_contradictory);

  return (
    <div
      className={`min-w-[190px] max-w-[220px] rounded-lg border p-2.5 text-xs shadow-md backdrop-blur-sm transition-all ${
        isContradictory
          ? 'border-rose-500/50 bg-rose-950/30 text-rose-200'
          : 'border-slate-700/80 bg-slate-900/90 text-slate-200'
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className={`!h-2 !w-2 !border-2 !border-slate-900 ${isContradictory ? '!bg-rose-400' : '!bg-emerald-400'}`}
      />

      <div className="flex items-center gap-1.5 mb-1.5">
        {isContradictory ? (
          <AlertTriangle className="h-3.5 w-3.5 text-rose-400 flex-shrink-0" />
        ) : (
          <BookOpen className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
        )}
        <span
          className={`text-[9px] font-bold uppercase tracking-wider ${
            isContradictory ? 'text-rose-400' : 'text-emerald-400'
          }`}
        >
          {isContradictory ? 'Conflict / Risk' : 'Supporting Evidence'}
        </span>
      </div>

      <p className="line-clamp-2 text-[11px] font-medium leading-snug text-slate-100" title={data.title}>
        {data.title || 'Experimental citation record'}
      </p>

      <div className="mt-2 flex items-center justify-between border-t border-slate-800 pt-1 text-[9px] text-slate-400">
        <span className="font-mono">{data.pmid ? `PMID:${data.pmid}` : 'Open Targets'}</span>
        <span className="rounded bg-slate-800 px-1 py-0.2 capitalize text-slate-300">
          {data.causality ? data.causality.replace(/_/g, ' ') : 'evidence'}
        </span>
      </div>
    </div>
  );
};
