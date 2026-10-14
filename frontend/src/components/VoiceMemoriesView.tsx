import React, { useState } from 'react';
import {
  Search,
  Plus,
  Trash2,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Tag,
  Clock,
  Sparkles,
  User,
  Radio,
  FileText,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import { MemoryItem, MemorySearchResponse } from '../types';
import { api } from '../services/api';

interface VoiceMemoriesViewProps {
  memories: MemoryItem[];
  loading: boolean;
  uid: string;
  onRefresh: () => void;
  onOpenAddModal: () => void;
}

export const VoiceMemoriesView: React.FC<VoiceMemoriesViewProps> = ({
  memories,
  loading,
  uid,
  onRefresh,
  onOpenAddModal,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [semanticMode, setSemanticMode] = useState(false);
  const [searching, setSearching] = useState(false);
  const [semanticResults, setSemanticResults] = useState<MemoryItem[] | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Perform semantic search via POST /api/memories/search
  const handleSemanticSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) {
      setSemanticResults(null);
      return;
    }
    setSearching(true);
    setActionError(null);
    try {
      const res: MemorySearchResponse = await api.searchMemories({
        uid,
        query: searchQuery.trim(),
        limit: 20,
        score_threshold: 0.1,
      });
      setSemanticResults(res.memories);
    } catch (err: any) {
      setActionError(err.message || 'Semantic search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSemanticResults(null);
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this memory item from Qdrant?')) return;
    setDeletingId(id);
    setActionError(null);
    try {
      await api.deleteMemory(id, uid);
      if (semanticResults) {
        setSemanticResults(semanticResults.filter((m) => m.id !== id));
      }
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || 'Failed to delete memory');
    } finally {
      setDeletingId(null);
    }
  };

  // Determine list to show
  const displayList = semanticResults !== null
    ? semanticResults
    : searchQuery.trim() && !semanticMode
    ? memories.filter(
        (m) =>
          m.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
          m.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (m.metadata?.speaker && m.metadata.speaker.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : memories;

  const getSourceBadge = (source?: string) => {
    switch (source) {
      case 'omi_conversation_summary':
        return {
          label: 'Conversation Summary',
          color: 'bg-purple-950/70 text-purple-300 border-purple-800/50',
          icon: FileText,
        };
      case 'omi_conversation_segment':
        return {
          label: 'Conversation Segment',
          color: 'bg-sky-950/70 text-sky-300 border-sky-800/50',
          icon: Radio,
        };
      case 'omi_realtime_segment':
        return {
          label: 'Realtime Stream',
          color: 'bg-emerald-950/70 text-emerald-300 border-emerald-800/50',
          icon: Radio,
        };
      case 'manual':
        return {
          label: 'Manual Ingestion',
          color: 'bg-amber-950/70 text-amber-300 border-amber-800/50',
          icon: Tag,
        };
      default:
        return {
          label: source || 'Memory Point',
          color: 'bg-slate-800 text-slate-300 border-slate-700',
          icon: Tag,
        };
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Radio className="w-6 h-6 text-sky-400" />
            Voice Memories Browser
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real memories retrieved directly from Qdrant Cloud collection{' '}
            <span className="font-mono text-sky-300">agentmemory_memories</span> for user{' '}
            <span className="font-mono text-sky-300">{uid}</span>.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:text-white hover:border-slate-700 transition-all"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
            Refresh
          </button>
          <button
            onClick={onOpenAddModal}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-xs font-semibold text-white shadow-md shadow-sky-600/25 transition-all transform active:scale-95"
          >
            <Plus className="w-4 h-4" />
            Add Memory
          </button>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="glass-panel rounded-2xl p-4 border border-slate-800/80 shadow-lg space-y-3">
        <form onSubmit={handleSemanticSearch} className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={
                semanticMode
                  ? "Enter natural language query for semantic cosine search..."
                  : "Filter memories by text, speaker, or ID..."
              }
              className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60 font-sans"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500 hover:text-slate-300"
              >
                Clear
              </button>
            )}
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto justify-end">
            <button
              type="button"
              onClick={() => {
                const nextMode = !semanticMode;
                setSemanticMode(nextMode);
                if (!nextMode) setSemanticResults(null);
                else if (searchQuery.trim()) handleSemanticSearch();
              }}
              className={`px-3 py-2 rounded-xl text-xs font-medium border flex items-center gap-1.5 transition-all ${
                semanticMode
                  ? 'bg-sky-950/80 text-sky-300 border-sky-600'
                  : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Semantic Match {semanticMode ? 'ON' : 'OFF'}</span>
            </button>

            {semanticMode && (
              <button
                type="submit"
                disabled={searching || !searchQuery.trim()}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md disabled:opacity-50 transition-all"
              >
                {searching ? 'Vectorizing...' : 'Search Vectors'}
              </button>
            )}
          </div>
        </form>

        {actionError && (
          <div className="p-3 rounded-xl bg-rose-950/50 border border-rose-800 text-xs text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{actionError}</span>
          </div>
        )}
      </div>

      {/* Memory Results Stats */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span>
          Showing <span className="font-semibold text-white">{displayList.length}</span> of{' '}
          <span className="font-semibold text-white">{memories.length}</span> stored memories
          {semanticResults !== null && (
            <span className="ml-2 text-sky-400 font-medium">
              (Semantic search for "{searchQuery}")
            </span>
          )}
        </span>
        <span className="text-slate-500">FastEmbed cosine index</span>
      </div>

      {/* Memory Cards Feed */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass-panel p-5 rounded-2xl border border-slate-800 animate-pulse space-y-3">
              <div className="h-4 bg-slate-800 rounded w-1/4" />
              <div className="h-4 bg-slate-850 rounded w-3/4" />
              <div className="h-3 bg-slate-850 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : displayList.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800 space-y-3">
          <Radio className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-white">No memories found</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            {searchQuery
              ? `No memories matched your query "${searchQuery}". Try a broader query or toggle Semantic Match.`
              : `No memories currently exist for user ID ${uid}. Speak into your Omi app or click "Add Memory" above.`}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {displayList.map((item) => {
            const badge = getSourceBadge(item.metadata?.source);
            const BadgeIcon = badge.icon;
            const isExpanded = expandedId === item.id;
            const isCopied = copiedId === item.id;
            const isDeleting = deletingId === item.id;

            return (
              <div
                key={item.id}
                className="glass-card rounded-2xl p-5 border transition-all duration-200 hover:shadow-lg space-y-3"
              >
                {/* Card Top Row: Badges, Score, and Actions */}
                <div className="flex flex-wrap items-center justify-between gap-2.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Source Badge */}
                    <span
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold border ${badge.color}`}
                    >
                      <BadgeIcon className="w-3.5 h-3.5" />
                      {badge.label}
                    </span>

                    {/* Speaker Tag if present */}
                    {item.metadata?.speaker && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-slate-900 border border-slate-800 text-slate-200">
                        <User className="w-3.5 h-3.5 text-sky-400" />
                        {item.metadata.speaker}
                      </span>
                    )}

                    {/* Cosine Score if semantic search */}
                    {item.score !== null && item.score !== undefined && (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 font-semibold">
                        Score: {(item.score * 100).toFixed(1)}%
                      </span>
                    )}

                    {/* Timestamp */}
                    <span className="inline-flex items-center gap-1.5 text-xs text-slate-400 font-mono">
                      <Clock className="w-3.5 h-3.5" />
                      {item.created_at ? new Date(item.created_at).toLocaleString() : 'Unknown date'}
                    </span>
                  </div>

                  {/* Actions: Copy ID & Delete */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleCopyId(item.id)}
                      title="Copy Memory ID"
                      className="p-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs transition-colors"
                    >
                      {isCopied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      disabled={isDeleting}
                      title="Delete Memory from Qdrant"
                      className="p-2 rounded-lg bg-slate-900 border border-slate-800 hover:border-rose-900/50 hover:bg-rose-950/30 text-slate-300 hover:text-rose-400 text-xs transition-colors disabled:opacity-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Card Content (Transcript Presentation) */}
                <div className="space-y-2.5">
                  {/* Primary Presentation Field */}
                  <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 text-slate-100 text-base leading-relaxed whitespace-pre-wrap font-sans selection:bg-sky-500/30">
                    {item.display_text || item.content}
                  </div>

                  {/* If product names were normalized, clearly display both fields without silent rewrite */}
                  {item.display_text && item.display_text !== item.content && (
                    <div className="p-3.5 rounded-xl bg-slate-900/70 border border-amber-500/20 text-xs space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-amber-300/90 font-medium flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                          Normalized Product Terminology Clarification
                        </span>
                        <span className="text-xs font-mono text-slate-400">Original preserved in vector memory</span>
                      </div>
                      <div className="text-xs font-mono text-slate-200 bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                        <span className="text-slate-400 text-xs uppercase tracking-wider block font-sans font-semibold mb-1">
                          Original Spoken Audio Evidence:
                        </span>
                        "{item.content}"
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Footer: Metadata Accordion */}
                <div className="pt-1">
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : item.id)}
                    className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-sky-300 font-mono transition-colors"
                  >
                    <span>ID: {item.id.slice(0, 8)}...{item.id.slice(-6)}</span>
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5 ml-1" /> : <ChevronDown className="w-3.5 h-3.5 ml-1" />}
                    <span className="text-slate-400 ml-1">
                      {isExpanded ? 'Hide Payload Metadata' : 'View Payload Metadata'}
                    </span>
                  </button>

                  {isExpanded && (
                    <div className="mt-3 p-4 rounded-xl bg-slate-950/90 border border-slate-800 text-xs font-mono text-slate-300 space-y-2 overflow-x-auto">
                      <div className="flex items-center justify-between text-slate-400 border-b border-slate-800/60 pb-1.5">
                        <span>Payload Metadata (Qdrant Point)</span>
                        <span>User: {item.uid}</span>
                      </div>
                      <pre className="text-xs text-sky-200/90 leading-normal">
                        {JSON.stringify(item.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
