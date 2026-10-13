import React from 'react';
import {
  Database,
  Brain,
  Radio,
  Cpu,
  Layers,
  ArrowRight,
  Sparkles,
  Activity,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Terminal,
  Mail,
} from 'lucide-react';
import { MemoryItem, HealthResponse, ExecutionEvent } from '../types';
import CircularCarousel from './reactbits/CircularCarousel';
import MagicBento from './reactbits/MagicBento';

interface DashboardViewProps {
  memories: MemoryItem[];
  health: HealthResponse | null;
  uid: string;
  onNavigate: (tab: string) => void;
  lastExecution: ExecutionEvent[] | null;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  memories,
  health,
  uid,
  onNavigate,
  lastExecution,
}) => {
  // Count conversation segments vs summaries
  const summariesCount = memories.filter((m) => m.metadata?.source === 'omi_conversation_summary').length;
  const segmentsCount = memories.filter(
    (m) => m.metadata?.source === 'omi_conversation_segment' || m.metadata?.source === 'omi_realtime_segment'
  ).length;

  // Unsplash images for the 3D circular carousel
  const carouselItems = [
    {
      src: 'https://images.unsplash.com/photo-1590602847861-f357a9332bbc?w=900&q=80&auto=format&fit=crop',
      alt: 'Omi Mobile Audio Ingestion',
      title: 'Omi Phone Audio',
      subtitle: 'Real-time Streaming Transcripts',
    },
    {
      src: 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=900&q=80&auto=format&fit=crop',
      alt: 'Qdrant Cloud Vector Store',
      title: 'Qdrant Cloud',
      subtitle: '384-d Cosine Embeddings',
    },
    {
      src: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=900&q=80&auto=format&fit=crop',
      alt: 'Lyzr Multi-Agent Orchestration',
      title: 'Lyzr Research Agent',
      subtitle: 'Grounded Memory Reasoning',
    },
    {
      src: 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=900&q=80&auto=format&fit=crop',
      alt: 'Multi-Agent Collaborative Workflows',
      title: 'Multi-Agent Engine',
      subtitle: 'Deduplicated Semantic Memory',
    },
    {
      src: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=900&q=80&auto=format&fit=crop',
      alt: 'Hackathon Demo 2026',
      title: 'Hackathon 2026',
      subtitle: 'Stop Prompting, Solo Agents',
    },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner / Hero Summary */}
      <div className="relative overflow-hidden rounded-2xl border border-sky-500/20 bg-gradient-to-br from-slate-900/90 via-[#0c1527]/90 to-sky-950/40 p-6 sm:p-8 backdrop-blur-xl shadow-2xl">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/15 text-sky-300 border border-sky-400/30">
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              Track 2: Collaborative Multi-Agent Workflows
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              LifeOS — Personal AI Operator
            </h1>
            <p className="text-slate-300 text-sm leading-relaxed">
              Voice-first operator that understands user intent via <span className="text-sky-300 font-semibold">Omi</span>, retrieves personal context from <span className="text-sky-300 font-semibold">Qdrant Cloud</span>, coordinates <span className="text-sky-300 font-semibold">Lyzr Specialist Agents</span>, stages & executes verified actions in <span className="text-sky-300 font-semibold">Google Calendar, Tasks, Gmail & Telegram</span> with human approval, and remembers completed outcomes.
            </p>
          </div>

          <div className="flex flex-wrap items-stretch sm:items-center gap-2">
            <button
              onClick={() => onNavigate('operator')}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium text-xs text-white bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 shadow-lg shadow-sky-500/25 transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Daily Operator</span>
            </button>
            <button
              onClick={() => onNavigate('drafts')}
              className="inline-flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl font-medium text-xs text-slate-200 bg-slate-900/80 hover:bg-slate-800 border border-slate-700/80 transition-all"
            >
              <Mail className="w-3.5 h-3.5 text-sky-400" />
              <span>Draft Email</span>
            </button>
            <button
              onClick={() => onNavigate('actions')}
              className="inline-flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl font-medium text-xs text-slate-200 bg-slate-900/80 hover:bg-slate-800 border border-slate-700/80 transition-all"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Approvals</span>
            </button>
          </div>
        </div>
      </div>

      {/* Primary Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Stored Memories */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Stored Memories</span>
            <div className="w-8 h-8 rounded-lg bg-sky-500/15 flex items-center justify-center text-sky-400">
              <Database className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">{memories.length}</span>
            <span className="text-xs text-sky-400 font-medium">points</span>
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-2">
            <span>{summariesCount} summaries</span>
            <span>•</span>
            <span>{segmentsCount} segments</span>
          </div>
        </div>

        {/* Vector Space */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Vector Store</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center text-indigo-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">384</span>
            <span className="text-xs text-indigo-400 font-medium">dimensions</span>
          </div>
          <div className="mt-2 text-xs text-slate-400 truncate">
            FastEmbed / BGE-Small (Cosine)
          </div>
        </div>

        {/* Lyzr Agent Status */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Reasoning Agent</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center text-emerald-400">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-xl font-bold text-white font-mono">Lyzr Agent</span>
          </div>
          <div className="mt-2 text-xs text-emerald-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Anti-Hallucination Guardrails</span>
          </div>
        </div>

        {/* Active Phone User ID */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800/80 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Omi User</span>
            <div className="w-8 h-8 rounded-lg bg-violet-500/15 flex items-center justify-center text-violet-400">
              <Radio className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 truncate">
            <span className="text-xs font-mono text-sky-300 font-semibold bg-slate-900/80 px-2 py-1 rounded border border-slate-800 inline-block max-w-full truncate">
              {uid}
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
            <span>Scoped tenant boundary</span>
          </div>
        </div>
      </div>

      {/* 3D Circular Carousel Section */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-xl overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-sky-400" />
              Core Architecture Showcase (3D Carousel)
            </h2>
            <p className="text-xs text-slate-400">
              Interactive 3D carousel demonstrating the multi-agent memory loop. Drag or use arrow keys to rotate.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">React Bits &lt;CircularCarousel /&gt;</span>
        </div>

        <div className="relative w-full h-[400px] overflow-hidden rounded-xl bg-slate-950/60 border border-slate-800/50">
          <CircularCarousel
            items={carouselItems}
            preset="cylinder"
            intro="rise"
            cardWidth={240}
            aspectRatio={1}
            speed={12}
            captions
          />
        </div>
      </div>

      {/* MagicBento Grid Section */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-400" />
              Telemetry & Capability Hub (MagicBento)
            </h2>
            <p className="text-xs text-slate-400">
              Interactive bento grid with spotlight, dynamic border glow, and live system metrics.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">React Bits &lt;MagicBento /&gt;</span>
        </div>

        <div className="relative rounded-xl overflow-hidden p-2 bg-slate-950/40 border border-slate-800/40">
          <MagicBento
            columns={3}
            rowHeight={220}
            gap={16}
            radius={18}
            enableBorderGlow={true}
            enableSpotlight={true}
            spotlightRadius={320}
            clickEffect={true}
          />
        </div>
      </div>

      {/* Recent Voice Memories Preview & Last Execution Trace */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Memories Feed */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Radio className="w-4 h-4 text-sky-400" />
                Latest Ingested Memories
              </h2>
              <button
                onClick={() => onNavigate('memories')}
                className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1"
              >
                View all ({memories.length})
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {memories.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs">
                No memories recorded yet for user <span className="font-mono text-slate-400">{uid}</span>.
              </div>
            ) : (
              <div className="space-y-3">
                {memories.slice(0, 3).map((item) => (
                  <div
                    key={item.id}
                    className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-sky-500/30 transition-all text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="font-mono px-1.5 py-0.5 rounded bg-slate-800 text-sky-300">
                        {item.metadata?.speaker || (item.metadata?.source === 'omi_conversation_summary' ? 'Summary' : 'Segment')}
                      </span>
                      <span>
                        {item.created_at ? new Date(item.created_at).toLocaleTimeString() : 'Recent'}
                      </span>
                    </div>
                    <p className="text-slate-200 line-clamp-2 leading-relaxed">
                      {item.content}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Workflow Execution Quick Trace */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                Latest Execution Telemetry
              </h2>
              <button
                onClick={() => onNavigate('execution')}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
              >
                Full Visualizer
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {lastExecution && lastExecution.length > 0 ? (
              <div className="space-y-2">
                {lastExecution.slice(-4).map((evt, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs font-mono"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      <span className="text-slate-300">{evt.step}</span>
                    </div>
                    <span className="text-slate-500 text-[10px]">
                      {new Date(evt.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500 text-xs space-y-2">
                <p>No query executions in this session yet.</p>
                <button
                  onClick={() => onNavigate('ask')}
                  className="px-3 py-1.5 rounded-lg bg-sky-600/20 text-sky-300 border border-sky-500/30 hover:bg-sky-600/30 text-xs font-medium"
                >
                  Run a query in Ask AgentMemory
                </button>
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
            <span>Pipeline: 5 stages (Validation → Retrieval → Synthesis → Lyzr → Response)</span>
            <span className="text-emerald-400 font-mono">Zero Hallucinations</span>
          </div>
        </div>
      </div>
    </div>
  );
};
