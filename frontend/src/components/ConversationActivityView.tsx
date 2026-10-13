import React, { useState } from 'react';
import {
  Radio,
  FileText,
  ListTodo,
  CheckCircle,
  Clock,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronUp,
  Info,
  Calendar,
  Mic,
  Tag,
} from 'lucide-react';
import { MemoryItem } from '../types';

interface ConversationActivityViewProps {
  memories: MemoryItem[];
  uid: string;
}

export const ConversationActivityView: React.FC<ConversationActivityViewProps> = ({
  memories,
  uid,
}) => {
  const [expandedConvId, setExpandedConvId] = useState<string | null>(null);

  // Filter conversation summaries and segments
  const summaries = memories.filter((m) => m.metadata?.source === 'omi_conversation_summary');
  const convSegments = memories.filter((m) => m.metadata?.source === 'omi_conversation_segment');
  const realtimeSegments = memories.filter((m) => m.metadata?.source === 'omi_realtime_segment');

  // Group segments by conversation_id
  const getSegmentsForConv = (convId?: string) => {
    if (!convId) return [];
    return convSegments.filter((s) => s.metadata?.conversation_id === convId);
  };

  return (
    <div className="space-y-8 animate-fadeIn max-w-4xl mx-auto">
      {/* View Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <Radio className="w-6 h-6 text-sky-400" />
          Omi Conversation Activity
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Recent conversation activity ingested from the Omi mobile application via secure public webhook endpoint.
        </p>
      </div>

      {/* Architecture Transparency Card */}
      <div className="glass-panel rounded-2xl p-4 sm:p-5 border border-sky-500/20 bg-sky-950/20 text-xs text-sky-200 space-y-2">
        <div className="flex items-center gap-2 font-semibold text-sky-300">
          <Info className="w-4 h-4 text-sky-400 shrink-0" />
          <span>Webhook Ingestion Architecture & Data Origin</span>
        </div>
        <p className="text-slate-300 leading-relaxed text-[11px]">
          Transcripts and summaries shown below are genuine Omi webhook deliveries received at{' '}
          <code className="text-sky-300 font-mono">POST /omi/conversation</code> and{' '}
          <code className="text-sky-300 font-mono">POST /omi/realtime</code>. Each segment is deduplicated via deterministic UUIDv5, indexed with FastEmbed 384-d vectors, and preserved in Qdrant Cloud under user boundary{' '}
          <code className="text-sky-300 font-mono">{uid}</code>.
        </p>
      </div>

      {/* Summary of Ingested Activity */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-panel p-4 rounded-xl border border-slate-800 text-xs space-y-1">
          <span className="text-slate-400">Completed Sessions</span>
          <div className="text-2xl font-extrabold text-white font-mono">{summaries.length}</div>
          <span className="text-[10px] text-purple-400 font-medium">Structured Overviews</span>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800 text-xs space-y-1">
          <span className="text-slate-400">Conversation Segments</span>
          <div className="text-2xl font-extrabold text-white font-mono">{convSegments.length}</div>
          <span className="text-[10px] text-sky-400 font-medium">Transcripts with Timestamps</span>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800 text-xs space-y-1">
          <span className="text-slate-400">Real-Time Segments</span>
          <div className="text-2xl font-extrabold text-white font-mono">{realtimeSegments.length}</div>
          <span className="text-[10px] text-emerald-400 font-medium">Streaming Speech Chunks</span>
        </div>
      </div>

      {/* Structured Conversations Feed */}
      <div className="space-y-6">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <FileText className="w-4 h-4 text-purple-400" />
          Completed Conversations ({summaries.length})
        </h2>

        {summaries.length === 0 ? (
          <div className="glass-panel rounded-2xl p-10 text-center border border-slate-800 text-xs text-slate-400 space-y-2">
            <Radio className="w-8 h-8 text-slate-600 mx-auto" />
            <p>No completed conversation summaries received yet for this user ID.</p>
            <p className="text-[11px] text-slate-500">
              When an Omi audio recording ends, Omi sends structured insights to <code className="text-sky-400">/omi/conversation</code>.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {summaries.map((summary) => {
              const convId = summary.metadata?.conversation_id;
              const relatedSegments = getSegmentsForConv(convId);
              const isExpanded = expandedConvId === summary.id;

              return (
                <div
                  key={summary.id}
                  className="glass-card rounded-2xl p-6 border border-slate-800 hover:border-slate-700 transition-all space-y-4 shadow-xl"
                >
                  {/* Title & Metadata Top Row */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-purple-400" />
                        {summary.metadata?.title || 'Voice Conversation Summary'}
                      </h3>
                      {convId && (
                        <p className="text-[10px] font-mono text-slate-400 mt-0.5">
                          Conv ID: {convId}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {summary.metadata?.category && (
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-purple-950/80 text-purple-300 border border-purple-800/60 uppercase">
                          {summary.metadata.category}
                        </span>
                      )}
                      <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {summary.created_at ? new Date(summary.created_at).toLocaleDateString() : 'Recent'}
                      </span>
                    </div>
                  </div>

                  {/* Summary & Action Items Content */}
                  <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 text-xs text-slate-200 whitespace-pre-wrap leading-relaxed font-sans">
                    {summary.content}
                  </div>

                  {/* Related Segments Accordion */}
                  {relatedSegments.length > 0 && (
                    <div className="pt-2">
                      <button
                        onClick={() => setExpandedConvId(isExpanded ? null : summary.id)}
                        className="flex items-center gap-1.5 text-xs font-medium text-sky-400 hover:text-sky-300"
                      >
                        <Mic className="w-3.5 h-3.5" />
                        <span>
                          {isExpanded
                            ? `Hide ${relatedSegments.length} Transcript Segments`
                            : `View ${relatedSegments.length} Spoken Transcript Segments`}
                        </span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>

                      {isExpanded && (
                        <div className="mt-3 space-y-2 pl-4 border-l-2 border-sky-500/30">
                          {relatedSegments.map((seg) => (
                            <div
                              key={seg.id}
                              className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs space-y-1"
                            >
                              <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                                <span className="text-sky-300 font-semibold">{seg.metadata?.speaker || 'Speaker'}</span>
                                {seg.metadata?.start !== undefined && (
                                  <span>
                                    {seg.metadata.start.toFixed(1)}s - {seg.metadata?.end?.toFixed(1) || '?'}s
                                  </span>
                                )}
                              </div>
                              <p className="text-slate-100">{seg.content}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Real-time Streaming Segments Stream */}
      {realtimeSegments.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Radio className="w-4 h-4 text-emerald-400" />
            Live Streaming Chunks ({realtimeSegments.length})
          </h2>
          <div className="space-y-2">
            {realtimeSegments.map((rt) => (
              <div
                key={rt.id}
                className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs space-y-1"
              >
                <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                  <span className="text-emerald-400 font-semibold">
                    {rt.metadata?.speaker || 'Live Stream'}
                  </span>
                  <span>{rt.created_at ? new Date(rt.created_at).toLocaleTimeString() : 'Live'}</span>
                </div>
                <p className="text-slate-100">{rt.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
