import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { Pill } from 'lucide-react';
import type { GraphNodeData } from '../../types';

export const DruggabilityNode: React.FC<{ data: GraphNodeData }> = ({ data }) => {
  return (
    <div className="min-w-[190px] max-w-[210px] rounded-lg border border-indigo-500/40 bg-slate-900/90 p-2.5 shadow-md backdrop-blur-sm">
      <Handle
        type="target"
        position={Position.Top}
        className="!h-2 !w-2 !border-2 !border-slate-900 !bg-indigo-400"
      />

      <div className="flex items-center justify-between gap-1 mb-1">
        <div className="flex items-center gap-1.5">
          <Pill className="h-3.5 w-3.5 text-indigo-400" />
          <span className="text-[9px] font-bold uppercase tracking-wider text-indigo-400">Tractability</span>
        </div>
        <span className="font-mono text-xs font-bold text-indigo-300">
          {data.tractability_score ? `${data.tractability_score}` : 'Assessed'}
        </span>
      </div>

      <div className="mt-1 flex flex-wrap gap-1">
        {data.modalities && data.modalities.length > 0 ? (
          data.modalities.map((m, idx) => (
            <span
              key={idx}
              className="rounded bg-indigo-950/80 border border-indigo-800/60 px-1.5 py-0.5 text-[9px] font-medium text-indigo-200"
            >
              {m}
            </span>
          ))
        ) : (
          <span className="text-[10px] text-slate-400">Modalities cataloged</span>
        )}
      </div>
    </div>
  );
};
