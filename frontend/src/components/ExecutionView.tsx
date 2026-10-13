import React, { useState } from 'react';
import {
  Terminal,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  Database,
  Cpu,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Activity,
  Layers,
  Brain,
} from 'lucide-react';
import { ExecutionEvent } from '../types';

interface ExecutionViewProps {
  events: ExecutionEvent[] | null;
  onNavigateToAsk: () => void;
}

export const ExecutionView: React.FC<ExecutionViewProps> = ({
  events,
  onNavigateToAsk,
}) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const STAGES_PIPELINE = [
    {
      key: 'request_validation',
      name: '1. Scope Validation',
      description: 'Enforces tenant boundary isolation and query limits.',
      icon: ShieldCheck,
    },
    {
      key: 'memory_retrieval',
      name: '2. Qdrant Retrieval',
      description: 'Queries 384-d FastEmbed vectors with cosine scoring.',
      icon: Database,
    },
    {
      key: 'prompt_synthesis',
      name: '3. Grounding Assembly',
      description: 'Assembles retrieved transcripts with anti-hallucination rules.',
      icon: Layers,
    },
    {
      key: 'fact_finder_agent',
      name: '4. Fact Finder Agent',
      description: 'Specialist 1 (6acd9f...): Extracts verified factual claims from memory.',
      icon: Cpu,
    },
    {
      key: 'data_analyst_agent',
      name: '5. Verifiable Analyst',
      description: 'Specialist 2 (6acd1e...): Structures action items and plans without assumptions.',
      icon: Cpu,
    },
    {
      key: 'agent_reasoning',
      name: '6. Manager Synthesis',
      description: 'Manager Agent (6acdcd...): Coordinated synthesis and authoritative answer.',
      icon: Brain,
    },
    {
      key: 'final_response',
      name: '7. Output Delivery',
      description: 'Returns synthesized response with supporting citations and audit trace.',
      icon: Activity,
    },
  ];

  return (
    <div className="space-y-8 animate-fadeIn max-w-4xl mx-auto">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Terminal className="w-6 h-6 text-sky-400" />
            Agent Execution Visualizer
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real step-by-step telemetry delivered directly by the FastAPI backend during memory reasoning.
          </p>
        </div>

        <button
          onClick={onNavigateToAsk}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-xs font-semibold text-white shadow-md shadow-sky-600/25 transition-all"
        >
          Run New Query
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Pipeline Overview Architecture Cards */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-xl space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          Collaborative Multi-Agent Reasoning Pipeline
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {STAGES_PIPELINE.map((stg, i) => {
            const Icon = stg.icon;
            // Check if step occurred in the active events
            const matchingEvent = events?.find((e) => e.step === stg.key);
            const isCompleted = matchingEvent?.status === 'completed';
            const isFailed = matchingEvent?.status === 'failed';
            const isStarted = matchingEvent?.status === 'started';

            return (
              <div
                key={stg.key}
                className={`p-3.5 rounded-xl border text-xs space-y-1.5 transition-all ${
                  isCompleted
                    ? 'bg-emerald-950/30 border-emerald-800/50 text-emerald-300'
                    : isFailed
                    ? 'bg-rose-950/30 border-rose-800/50 text-rose-300'
                    : isStarted
                    ? 'bg-sky-950/30 border-sky-800/50 text-sky-300'
                    : 'bg-slate-900/60 border-slate-800 text-slate-400'
                }`}
              >
                <div className="flex items-center justify-between">
                  <Icon className="w-4 h-4 text-sky-400" />
                  <span className="text-[10px] font-mono">Stage 0{i + 1}</span>
                </div>
                <div className="font-semibold text-white truncate text-[11px]">{stg.name.split('. ')[1]}</div>
                <div className="text-[10px] text-slate-400 line-clamp-2 leading-tight">
                  {stg.description}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Real Execution Trace List */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-xl space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Clock className="w-4 h-4 text-sky-400" />
            Execution Event Stream
          </h2>
          <span className="text-xs font-mono text-slate-400">
            {events ? `${events.length} events logged` : 'No events'}
          </span>
        </div>

        {!events || events.length === 0 ? (
          <div className="p-12 text-center border border-dashed border-slate-800 rounded-xl space-y-3">
            <Terminal className="w-10 h-10 text-slate-600 mx-auto" />
            <h3 className="text-base font-bold text-white">No Execution Events Recorded Yet</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Execute a question in the "Ask AgentMemory" tab to trigger the live reasoning pipeline and view real telemetry.
            </p>
            <button
              onClick={onNavigateToAsk}
              className="px-4 py-2 rounded-xl bg-sky-600/30 hover:bg-sky-600/50 text-sky-300 border border-sky-500/40 text-xs font-medium"
            >
              Go to Ask AgentMemory
            </button>
          </div>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
            {events.map((evt, idx) => {
              const isCompleted = evt.status === 'completed';
              const isFailed = evt.status === 'failed';
              const isStarted = evt.status === 'started';
              const isExpanded = expandedIndex === idx;

              return (
                <div key={idx} className="relative group">
                  {/* Timeline Node Dot */}
                  <div
                    className={`absolute -left-6 top-1.5 w-5 h-5 rounded-full border-2 bg-slate-950 flex items-center justify-center -translate-x-1/2 ${
                      isCompleted
                        ? 'border-emerald-500 text-emerald-400'
                        : isFailed
                        ? 'border-rose-500 text-rose-400'
                        : isStarted
                        ? 'border-sky-500 text-sky-400'
                        : 'border-slate-700 text-slate-500'
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : isFailed ? (
                      <AlertCircle className="w-3 h-3" />
                    ) : (
                      <div className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
                    )}
                  </div>

                  {/* Event Card */}
                  <div className="glass-card rounded-xl p-4 border transition-all text-xs space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-white text-sm">
                          {evt.step}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-semibold ${
                            isCompleted
                              ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                              : isFailed
                              ? 'bg-rose-950/80 text-rose-400 border border-rose-800/60'
                              : 'bg-sky-950/80 text-sky-400 border border-sky-800/60'
                          }`}
                        >
                          {evt.status}
                        </span>
                      </div>

                      <span className="text-[11px] font-mono text-slate-400">
                        {new Date(evt.timestamp).toISOString()}
                      </span>
                    </div>

                    {/* Expandable Details Payload */}
                    {evt.details && Object.keys(evt.details).length > 0 && (
                      <div className="pt-2">
                        <button
                          onClick={() => setExpandedIndex(isExpanded ? null : idx)}
                          className="flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 font-mono"
                        >
                          <span>{isExpanded ? 'Hide Payload' : 'Inspect Telemetry Payload'}</span>
                          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>

                        {isExpanded && (
                          <div className="mt-2 p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
                            <pre className="text-sky-200/90 leading-tight">
                              {JSON.stringify(evt.details, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
