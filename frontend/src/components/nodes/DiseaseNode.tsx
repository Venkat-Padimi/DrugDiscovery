import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { Dna, CheckCircle2 } from 'lucide-react';
import type { GraphNodeData } from '../../types';

export const DiseaseNode: React.FC<{ data: GraphNodeData }> = ({ data }) => {
  return (
    <div className="min-w-[240px] rounded-xl border border-cyan-500/40 bg-slate-900/95 p-4 shadow-xl backdrop-blur-md transition-all hover:border-cyan-400">
      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/20 text-cyan-400">
          <Dna className="h-5 w-5 animate-pulse" />
        </div>
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">Target Pathology</span>
          <h3 className="text-sm font-semibold text-slate-100">{data.label || data.entity || 'Pathology'}</h3>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-slate-800 pt-2 text-[11px] text-slate-400">
        <span className="flex items-center gap-1">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
          {data.total_targets ? `${data.total_targets} Candidates` : 'Active'}
        </span>
        <span className="font-mono text-cyan-300">{data.session_id || 'ACTIVE'}</span>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-3 !border-2 !border-slate-900 !bg-cyan-400"
      />
    </div>
  );
};
