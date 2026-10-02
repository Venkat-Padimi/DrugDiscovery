import React, { useState, useMemo } from 'react';
import type { AgentTraceEvent } from '../../types';
import {
  Activity,
  CheckCircle2,
  Clock,
  Wrench,
} from 'lucide-react';

interface AuditTraceViewProps {
  trace: AgentTraceEvent[];
}

export const AuditTraceView: React.FC<AuditTraceViewProps> = ({ trace }) => {
  const [selectedAgent, setSelectedAgent] = useState('ALL');

  const agentNames = useMemo(() => {
    const names = Array.from(new Set(trace.map((t) => t.agent_name)));
    return ['ALL', ...names];
  }, [trace]);

  const filteredTrace = useMemo(() => {
    if (selectedAgent === 'ALL') return trace;
    return trace.filter((t) => t.agent_name === selectedAgent);
  }, [trace, selectedAgent]);

  const totalDuration = trace.reduce((acc, curr) => acc + (curr.duration_ms || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">Total Audit Events</div>
          <div className="mt-1 font-mono text-2xl font-bold text-white">{trace.length}</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">Total Agent Execution Time</div>
          <div className="mt-1 font-mono text-2xl font-bold text-cyan-400">
            {(totalDuration / 1000).toFixed(2)}s
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs font-medium text-slate-400">Execution Status</div>
          <div className="mt-1 flex items-center gap-1.5 font-bold text-emerald-400">
            <CheckCircle2 className="h-5 w-5" />
            <span>Completed Successfully</span>
          </div>
        </div>
      </div>

      {/* Main Trace Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md shadow-xl overflow-hidden">
        {/* Filter Toolbar */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">LangGraph Agent Execution Timeline</h3>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Filter Agent:</span>
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
            >
              {agentNames.map((name) => (
                <option key={name} value={name}>
                  {name === 'ALL' ? 'All Workflow Agents' : name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Chronological Event Cards */}
        <div className="p-6 space-y-4">
          {filteredTrace.map((event, idx) => {
            const isSuccess = event.status === 'success';

            return (
              <div
                key={event.event_id || idx}
                className="relative pl-6 before:absolute before:left-2 before:top-3 before:bottom-0 before:w-0.5 before:bg-slate-800 last:before:hidden"
              >
                <div
                  className={`absolute left-0 top-2 h-4 w-4 rounded-full border-2 border-slate-950 ${
                    isSuccess ? 'bg-cyan-400' : 'bg-rose-400'
                  }`}
                />

                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4 text-xs transition-all hover:border-slate-700">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-sm">{event.agent_name}</span>
                      <span className="rounded bg-slate-800 font-mono text-[10px] text-cyan-300 px-2 py-0.5">
                        {event.stage}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-slate-400 text-[11px] font-mono">
                      {event.duration_ms !== undefined && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3 text-slate-500" />
                          {event.duration_ms.toFixed(1)} ms
                        </span>
                      )}
                      <span
                        className={`rounded px-1.5 py-0.2 font-semibold uppercase text-[10px] ${
                          isSuccess ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                        }`}
                      >
                        {event.status}
                      </span>
                    </div>
                  </div>

                  {event.input_summary && (
                    <div className="mb-1 text-slate-400">
                      <strong className="text-slate-300">Input: </strong>
                      {event.input_summary}
                    </div>
                  )}

                  {event.output_summary && (
                    <div className="text-slate-300">
                      <strong className="text-cyan-400">Output: </strong>
                      {event.output_summary}
                    </div>
                  )}

                  {event.tool_calls && event.tool_calls.length > 0 && (
                    <div className="mt-2.5 flex items-center gap-1.5 border-t border-slate-800/80 pt-2 text-[11px]">
                      <Wrench className="h-3 w-3 text-slate-500" />
                      <span className="text-slate-500">Tools:</span>
                      <div className="flex flex-wrap gap-1">
                        {event.tool_calls.map((tool, i) => (
                          <span
                            key={i}
                            className="rounded bg-slate-900 border border-slate-800 px-1.5 py-0.2 font-mono text-[10px] text-slate-300"
                          >
                            {tool}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
