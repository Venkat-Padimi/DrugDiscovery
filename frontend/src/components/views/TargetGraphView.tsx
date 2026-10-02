import React, { useState, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { DiseaseNode } from '../nodes/DiseaseNode';
import { TargetNode } from '../nodes/TargetNode';
import { EvidenceNode } from '../nodes/EvidenceNode';
import { DruggabilityNode } from '../nodes/DruggabilityNode';
import { CompoundNode } from '../nodes/CompoundNode';
import type { DiscoveryGraphData, GraphNodeData } from '../../types';
import {
  Network,
  Info,
  X,
} from 'lucide-react';

interface TargetGraphViewProps {
  graphData: DiscoveryGraphData;
  onSelectTarget: (symbol: string) => void;
}

export const TargetGraphView: React.FC<TargetGraphViewProps> = ({ graphData, onSelectTarget }) => {
  const nodeTypes = useMemo(
    () => ({
      diseaseNode: DiseaseNode,
      targetNode: TargetNode,
      evidenceNode: EvidenceNode,
      druggabilityNode: DruggabilityNode,
      compoundNode: CompoundNode,
    }),
    []
  );

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>(graphData.nodes as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(graphData.edges as Edge[]);
  const [selectedNode, setSelectedNode] = useState<{ id: string; type: string; data: GraphNodeData } | null>(null);
  const [filterType, setFilterType] = useState<string>('all');

  useEffect(() => {
    if (graphData.nodes && graphData.nodes.length > 0) {
      if (filterType === 'all') {
        setNodes(graphData.nodes as Node[]);
        setEdges(graphData.edges as Edge[]);
      } else if (filterType === 'targets_only') {
        const targetNodes = graphData.nodes.filter(
          (n) => n.type === 'diseaseNode' || n.type === 'targetNode'
        );
        const nodeIds = new Set(targetNodes.map((n) => n.id));
        const filteredEdges = graphData.edges.filter(
          (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
        );
        setNodes(targetNodes as Node[]);
        setEdges(filteredEdges as Edge[]);
      } else if (filterType === 'compounds') {
        const compNodes = graphData.nodes.filter(
          (n) => n.type === 'diseaseNode' || n.type === 'targetNode' || n.type === 'compoundNode'
        );
        const nodeIds = new Set(compNodes.map((n) => n.id));
        const filteredEdges = graphData.edges.filter(
          (e) => nodeIds.has(e.source) && nodeIds.has(e.target)
        );
        setNodes(compNodes as Node[]);
        setEdges(filteredEdges as Edge[]);
      }
    }
  }, [graphData, filterType, setNodes, setEdges]);

  const onNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNode({ id: node.id, type: node.type || 'unknown', data: node.data as GraphNodeData });
    if (node.type === 'targetNode' && node.data?.symbol) {
      onSelectTarget(node.data.symbol as string);
    }
  };

  return (
    <div className="relative h-[calc(100vh-180px)] min-h-[640px] w-full rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden shadow-2xl">
      {/* Top Floating Controls Bar */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/90 p-2 backdrop-blur-md">
        <div className="flex items-center gap-1.5 px-2 text-xs font-semibold text-slate-300">
          <Network className="h-4 w-4 text-cyan-400" />
          <span>Interactive Target Discovery Graph</span>
        </div>

        <div className="h-4 w-px bg-slate-800" />

        <div className="flex items-center gap-1">
          <button
            onClick={() => setFilterType('all')}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
              filterType === 'all'
                ? 'bg-cyan-950 border border-cyan-800 text-cyan-300'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Entities ({graphData.nodes?.length || 0})
          </button>
          <button
            onClick={() => setFilterType('targets_only')}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
              filterType === 'targets_only'
                ? 'bg-cyan-950 border border-cyan-800 text-cyan-300'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Targets Only
          </button>
          <button
            onClick={() => setFilterType('compounds')}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-all ${
              filterType === 'compounds'
                ? 'bg-cyan-950 border border-cyan-800 text-cyan-300'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            With Compounds
          </button>
        </div>
      </div>

      {/* Main React Flow Canvas */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        minZoom={0.2}
        maxZoom={2.0}
        attributionPosition="bottom-left"
        className="bg-slate-950"
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#1e293b" />
        <Controls className="!border-slate-800 !bg-slate-900 !text-slate-200" />
        <MiniMap
          nodeColor={(n) => {
            if (n.type === 'diseaseNode') return '#06b6d4';
            if (n.type === 'targetNode') return '#10b981';
            if (n.type === 'evidenceNode') return '#3b82f6';
            if (n.type === 'compoundNode') return '#8b5cf6';
            return '#6366f1';
          }}
          className="!border-slate-800 !bg-slate-900/90 !rounded-xl"
        />
      </ReactFlow>

      {/* Graph Legend Overlay */}
      <div className="absolute bottom-4 left-4 z-10 hidden sm:flex items-center gap-3 rounded-xl border border-slate-800/80 bg-slate-900/80 px-3 py-2 text-[11px] text-slate-400 backdrop-blur-md">
        <span className="font-semibold text-slate-300">Legend:</span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-400" /> Disease
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" /> Target
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-blue-400" /> Evidence
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-indigo-400" /> Tractability
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-teal-400" /> ChEMBL Active
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-purple-400" /> In Silico Prediction
        </span>
      </div>

      {/* Node Inspector Drawer */}
      {selectedNode && (
        <div className="absolute top-4 right-4 z-20 w-80 max-h-[calc(100%-32px)] overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900/95 p-4 shadow-2xl backdrop-blur-md">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-cyan-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                Entity Inspector
              </h4>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="mt-3 space-y-3 text-xs">
            <div>
              <span className="text-[10px] uppercase text-slate-500 font-semibold">Entity Type</span>
              <p className="font-mono text-cyan-300">{selectedNode.type}</p>
            </div>

            {selectedNode.data.symbol && (
              <div>
                <span className="text-[10px] uppercase text-slate-500 font-semibold">Symbol</span>
                <p className="font-bold text-white text-base">{selectedNode.data.symbol}</p>
                {selectedNode.data.name && (
                  <p className="text-slate-400 text-[11px]">{selectedNode.data.name}</p>
                )}
              </div>
            )}

            {selectedNode.data.score !== undefined && (
              <div className="flex items-center justify-between rounded-lg bg-slate-800/80 p-2">
                <span className="text-slate-400">Deterministic Score:</span>
                <span className="font-mono text-base font-bold text-cyan-300">
                  {selectedNode.data.score.toFixed(1)}
                </span>
              </div>
            )}

            {selectedNode.data.tier && (
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Confidence Tier:</span>
                <span className="rounded bg-emerald-500/20 px-2 py-0.5 font-semibold text-emerald-400 uppercase">
                  {selectedNode.data.tier}
                </span>
              </div>
            )}

            {selectedNode.data.title && (
              <div>
                <span className="text-[10px] uppercase text-slate-500 font-semibold">Citation Title</span>
                <p className="text-slate-200 font-medium">{selectedNode.data.title}</p>
                {selectedNode.data.pmid && (
                  <a
                    href={`https://pubmed.ncbi.nlm.nih.gov/${selectedNode.data.pmid}/`}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-block text-[11px] text-cyan-400 underline hover:text-cyan-300"
                  >
                    View PMID {selectedNode.data.pmid} &rarr;
                  </a>
                )}
              </div>
            )}

            {selectedNode.data.compound_name && (
              <div>
                <span className="text-[10px] uppercase text-slate-500 font-semibold">Molecule</span>
                <p className="font-bold text-slate-100">{selectedNode.data.compound_name}</p>
                <p className="font-mono text-[11px] text-teal-300">
                  {selectedNode.data.activity || selectedNode.data.predicted_kd}
                </p>
              </div>
            )}

            {selectedNode.data.disclaimer && (
              <div className="rounded-lg border border-purple-800/50 bg-purple-950/40 p-2 text-[10px] text-purple-300">
                <span className="font-bold">Disclaimer: </span>
                {selectedNode.data.disclaimer}
              </div>
            )}

            {selectedNode.type === 'targetNode' && (
              <div className="pt-2">
                <button
                  onClick={() => onSelectTarget(selectedNode.data.symbol as string)}
                  className="w-full rounded-lg bg-cyan-600/30 border border-cyan-500/40 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-600/50 transition-colors"
                >
                  Open Candidate Deep Dive &rarr;
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
