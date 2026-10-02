import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { FlaskConical, Cpu, AlertCircle } from 'lucide-react';
import type { GraphNodeData } from '../../types';

export const CompoundNode: React.FC<{ data: GraphNodeData }> = ({ data }) => {
  const isEmpirical = Boolean(data.is_empirical);

  return (
    <div
      className={`min-w-[200px] max-w-[230px] rounded-lg border p-2.5 shadow-md backdrop-blur-sm transition-all ${
        isEmpirical
          ? 'border-teal-500/50 bg-teal-950/40 text-teal-200'
          : 'border-purple-500/50 bg-purple-950/40 text-purple-200'
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className={`!h-2 !w-2 !border-2 !border-slate-900 ${isEmpirical ? '!bg-teal-400' : '!bg-purple-400'}`}
      />

      <div className="flex items-center justify-between gap-1 mb-1">
        <div className="flex items-center gap-1.5">
          {isEmpirical ? (
            <FlaskConical className="h-3.5 w-3.5 text-teal-400" />
          ) : (
            <Cpu className="h-3.5 w-3.5 text-purple-400" />
          )}
          <span
            className={`text-[9px] font-bold uppercase tracking-wider ${
              isEmpirical ? 'text-teal-400' : 'text-purple-400'
            }`}
          >
            {isEmpirical ? 'ChEMBL Bioactive' : 'In Silico Screened'}
          </span>
        </div>
      </div>

      <h5 className="truncate font-mono text-xs font-bold text-slate-100" title={data.compound_name || data.compound_id}>
        {data.compound_name || data.compound_id}
      </h5>

      <div className="mt-1 flex items-center justify-between text-[10px]">
        <span className="font-mono text-slate-300">{data.activity || data.predicted_kd || 'Active'}</span>
      </div>

      {/* Mandatory In Silico Disclaimer */}
      {!isEmpirical && (
        <div className="mt-1.5 flex items-start gap-1 rounded bg-purple-950/90 p-1 text-[8.5px] text-purple-300 border border-purple-800/40 leading-tight">
          <AlertCircle className="h-2.5 w-2.5 text-purple-400 flex-shrink-0 mt-0.5" />
          <span>Simulation prediction — not experimentally validated</span>
        </div>
      )}
    </div>
  );
};
