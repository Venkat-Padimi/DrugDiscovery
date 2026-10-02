import React, { useState } from 'react';
import type { ResearchGraphState } from '../../types';
import {
  FileText,
  Download,
  Copy,
  Check,
  AlertTriangle,
} from 'lucide-react';

interface ReportViewProps {
  state: ResearchGraphState;
}

export const ReportView: React.FC<ReportViewProps> = ({ state }) => {
  const [copied, setCopied] = useState(false);

  const downloadFile = (content: string, fileName: string, contentType: string) => {
    const a = document.createElement('a');
    const file = new Blob([content], { type: contentType });
    a.href = URL.createObjectURL(file);
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const handleDownloadMarkdown = () => {
    const md = generateMarkdownText();
    downloadFile(md, `${state.session_id || 'research'}_report.md`, 'text/markdown');
  };

  const handleDownloadJSON = () => {
    const jsonStr = JSON.stringify(state, null, 2);
    downloadFile(jsonStr, `${state.session_id || 'research'}_state.json`, 'application/json');
  };

  const handleDownloadCSV = () => {
    const rankings = state.target_rankings || [];
    const headers = [
      'Rank',
      'Symbol',
      'Name',
      'Priority_Score',
      'Confidence_Tier',
      'Tractability',
      'Assay_Status',
      'Evidence_Count',
    ];
    const rows = rankings.map((r, i) => [
      i + 1,
      r.target_symbol,
      `"${r.target_name || ''}"`,
      r.overall_priority_score.toFixed(1),
      r.confidence_tier,
      `"${r.tractability_summary || ''}"`,
      `"${r.experimental_validation_status || ''}"`,
      r.evidence_count || 0,
    ]);
    const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    downloadFile(csvContent, `${state.session_id || 'research'}_targets.csv`, 'text/csv');
  };

  const generateMarkdownText = (): string => {
    const rankings = state.target_rankings || [];
    let md = `# Therapeutic Target Prioritization Report\n\n`;
    md += `**Session ID**: \`${state.session_id}\`  \n`;
    md += `**Pathology / Disease**: ${state.disease_name}  \n`;
    md += `**Research Question**: ${state.research_question}  \n`;
    md += `**Date**: ${new Date().toISOString()}  \n\n`;

    md += `## Executive Summary\n\n`;
    md += `${state.executive_summary || 'Autonomous multi-agent investigation completed.'}\n\n`;

    md += `## Prioritized Candidate Targets\n\n`;
    md += `| Rank | Target | Priority Score | Tier | Tractability | Validation Status |\n`;
    md += `| :--- | :--- | :--- | :--- | :--- | :--- |\n`;
    rankings.forEach((r, idx) => {
      md += `| #${idx + 1} | **${r.target_symbol}** | ${r.overall_priority_score.toFixed(1)} | ${r.confidence_tier.toUpperCase()} | ${r.tractability_summary || 'N/A'} | ${r.experimental_validation_status || 'N/A'} |\n`;
    });
    md += `\n`;

    md += `## Mandatory Scientific Disclaimers\n\n`;
    md += `> **Computational In Silico Predictions**: All computational screening models, docking affinities, and simulation outputs are in silico approximations and have not been experimentally measured in biological assays.\n\n`;
    return md;
  };

  const handleCopyMarkdown = () => {
    navigator.clipboard.writeText(generateMarkdownText());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const rankings = state.target_rankings || [];

  return (
    <div className="space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-md shadow-xl">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <FileText className="h-5 w-5 text-cyan-400" />
            Synthesized Research Report
          </h2>
          <p className="text-xs text-slate-400">
            Export comprehensive multi-modal dossier with ranked candidates, citations, and disclaimers.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleCopyMarkdown}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            <span>{copied ? 'Copied' : 'Copy MD'}</span>
          </button>

          <button
            onClick={handleDownloadMarkdown}
            className="flex items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-950/60 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/40 transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Markdown (.md)</span>
          </button>

          <button
            onClick={handleDownloadCSV}
            className="flex items-center gap-1.5 rounded-lg border border-teal-500/40 bg-teal-950/60 px-3 py-1.5 text-xs font-semibold text-teal-300 hover:bg-teal-900/40 transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Target CSV (.csv)</span>
          </button>

          <button
            onClick={handleDownloadJSON}
            className="flex items-center gap-1.5 rounded-lg border border-purple-500/40 bg-purple-950/60 px-3 py-1.5 text-xs font-semibold text-purple-300 hover:bg-purple-900/40 transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            <span>State JSON (.json)</span>
          </button>
        </div>
      </div>

      {/* Rendered Scientific Document */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-8 backdrop-blur-md shadow-2xl space-y-6 text-slate-200">
        {/* Document Header */}
        <div className="border-b border-slate-800 pb-5">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>PLATFORM: DRUG DISCOVERY RESEARCH WORKBENCH</span>
            <span className="font-mono">SESSION: {state.session_id}</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            Therapeutic Target Prioritization Report
          </h1>
          <p className="text-sm text-cyan-400 font-medium mt-1">
            Pathology: {state.disease_name || 'Biomedical Investigation'}
          </p>
        </div>

        {/* Executive Summary */}
        <div className="space-y-2">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">Executive Summary</h3>
          <p className="rounded-xl bg-slate-950/70 border border-slate-800/80 p-4 text-xs leading-relaxed text-slate-300">
            {state.executive_summary ||
              'Autonomous multi-agent investigation successfully prioritized therapeutic targets using multi-modal data integration.'}
          </p>
        </div>

        {/* Ranked Targets Table */}
        <div className="space-y-3">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">
            Prioritized Candidates Matrix
          </h3>
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/90 text-slate-400 uppercase text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">Rank</th>
                  <th className="py-2.5 px-3">Symbol</th>
                  <th className="py-2.5 px-3">Score</th>
                  <th className="py-2.5 px-3">Tier</th>
                  <th className="py-2.5 px-3">Tractability</th>
                  <th className="py-2.5 px-3">Validation Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 bg-slate-900/40">
                {rankings.map((r, i) => (
                  <tr key={r.target_symbol}>
                    <td className="py-2.5 px-3 font-mono font-bold text-slate-400">#{i + 1}</td>
                    <td className="py-2.5 px-3 font-bold text-white">{r.target_symbol}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-cyan-300">
                      {r.overall_priority_score.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-3 font-semibold uppercase">{r.confidence_tier}</td>
                    <td className="py-2.5 px-3 text-slate-400">{r.tractability_summary || 'N/A'}</td>
                    <td className="py-2.5 px-3 text-slate-400">
                      {r.experimental_validation_status || 'Unassayed'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Scientific Disclaimers Box */}
        <div className="rounded-xl border border-purple-800/50 bg-purple-950/30 p-4 space-y-1.5 text-xs text-purple-200">
          <div className="flex items-center gap-2 font-bold text-purple-100">
            <AlertTriangle className="h-4 w-4 text-purple-400" />
            <span>Scientific Provenance & In Silico Disclaimers</span>
          </div>
          <p className="text-[11px] leading-relaxed text-purple-300">
            All bioactivity predictions produced via molecular docking or computational simulation pipelines represent
            in silico approximations and have not been validated in biological bench assays. Do not initiate in vivo
            dosing without confirmatory in vitro binding and functional assays.
          </p>
        </div>
      </div>
    </div>
  );
};
