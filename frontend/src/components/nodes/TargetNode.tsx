import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { Target } from 'lucide-react';
import type { GraphNodeData } from '../../types';

export const TargetNode: React.FC<{ data: GraphNodeData }> = ({ data }) => {
  const tierColor =
    data.tier?.toLowerCase() === 'high'
      ? 'border-emerald-500/50 bg-emerald-950/40 text-emerald-300'
      : data.tier?.toLowerCase() === 'medium'
      ? 'border-sky-500/50 bg-sky-950/40 text-sky-300'
      : 'border-amber-500/50 bg-amber-950/40 text-amber-300';

  const badgeColor =
    data.tier?.toLowerCase() === 'high'
      ? 'bg-emerald-500/20 text-emerald-400'
      : data.tier?.toLowerCase() === 'medium'
      ? 'bg-sky-500/20 text-sky-400'
      : 'bg-amber-500/20 text-amber-400';

  return (
    <div className={`min-w-[220px] rounded-xl border p-3.5 shadow-lg backdrop-blur-md transition-all hover:scale-[1.02] ${tierColor}`}>
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2.5 !w-2.5 !border-2 !border-slate-900 !bg-sky-400"
      />

      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-800 text-sky-400">
            <Target className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-base font-bold text-white tracking-wide">{data.symbol}</h4>
            <p className="max-w-[130px] truncate text-[10px] text-slate-300">{data.name || data.symbol}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-base font-extrabold text-cyan-300">{data.score?.toFixed(1) || '0.0'}</div>
          <div className="text-[9px] uppercase tracking-wider text-slate-400">Score</div>
        </div>
      </div>

      <div className="mt-2.5 flex items-center justify-between border-t border-slate-800/80 pt-2 text-[10px]">
        <span className={`rounded px-1.5 py-0.5 font-semibold uppercase tracking-wider ${badgeColor}`}>
          {data.tier || 'MEDIUM'}
        </span>
        <span className="truncate max-w-[110px] text-slate-300" title={data.tractability}>
          {data.tractability || 'Unassessed'}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-2.5 !w-2.5 !border-2 !border-slate-900 !bg-sky-400"
      />
    </div>
  );
};
