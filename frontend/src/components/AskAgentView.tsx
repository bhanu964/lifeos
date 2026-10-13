import React, { useState } from 'react';
import {
  Brain,
  Send,
  Sparkles,
  Cpu,
  Layers,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import { AskResponse, AskRequest, ExecutionEvent } from '../types';
import { api } from '../services/api';

interface AskAgentViewProps {
  uid: string;
  onExecutionUpdate: (events: ExecutionEvent[]) => void;
  onNavigateToExecution: () => void;
}

export const AskAgentView: React.FC<AskAgentViewProps> = ({
  uid,
  onExecutionUpdate,
  onNavigateToExecution,
}) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Suggestions derived from the actual phone recording!
  const suggestions = [
    'What did I say about my AgentMemory AI project?',
    'Which vector database is used for persistent memory?',
    'What goal was stated regarding the React dashboard?',
    'What are the action items from my conversation?',
  ];

  const handleAsk = async (queryText?: string) => {
    const q = (queryText || question).trim();
    if (!q) return;

    if (queryText) setQuestion(queryText);
    setLoading(true);
    setError(null);

    try {
      const askReq: AskRequest = {
        uid,
        question: q,
      };
      const res: AskResponse = await api.askAgent(askReq);
      setResponse(res);
      if (res.execution_events) {
        onExecutionUpdate(res.execution_events);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to execute query with Lyzr Agent');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn max-w-4xl mx-auto">
      {/* View Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
          <Brain className="w-3.5 h-3.5 text-indigo-400" />
          Lyzr Research Agent Reasoning Engine
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Ask AgentMemory
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto">
          Queries are matched against your private voice transcripts in Qdrant and synthesized by the{' '}
          <span className="text-sky-300 font-semibold">Lyzr Agent</span> with strict zero-hallucination ground truth.
        </p>
      </div>

      {/* Question Form */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-2xl space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk();
          }}
          className="space-y-3"
        >
          <div className="relative">
            <textarea
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything about what you spoke into your Omi app (e.g. 'What did I say about my AgentMemory AI project?')..."
              className="w-full p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60 font-sans resize-none"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-500 font-mono">
              Target UID: <span className="text-sky-300">{uid}</span>
            </div>

            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-xs text-white bg-gradient-to-r from-sky-600 via-sky-500 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 shadow-lg shadow-sky-600/25 transition-all transform active:scale-95 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Reasoning...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Ask Lyzr Agent</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Suggestion Pills */}
        <div className="pt-2 border-t border-slate-800/60">
          <div className="text-[11px] text-slate-400 font-medium mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-amber-400" />
            <span>Try asking from your real phone session:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((s, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleAsk(s)}
                className="text-xs px-3 py-1.5 rounded-lg bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 hover:border-sky-500/40 transition-all text-left"
              >
                "{s}"
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Loading Reasoning State */}
      {loading && (
        <div className="glass-panel rounded-2xl p-6 border border-sky-500/30 shadow-xl space-y-4 animate-pulse">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-sky-500/20 flex items-center justify-center text-sky-400">
              <Brain className="w-4 h-4 animate-spin" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Collaborative Multi-Agent Reasoning in Progress</h3>
              <p className="text-xs text-slate-400">Coordinating Fact Finder, Data Analyst, and Manager Agent...</p>
            </div>
          </div>

          <div className="space-y-2 pt-2 text-xs font-mono">
            <div className="flex items-center gap-2 text-sky-300">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>1. Request validated for user scope {uid}</span>
            </div>
            <div className="flex items-center gap-2 text-sky-300">
              <div className="w-3.5 h-3.5 rounded-full border border-sky-400 border-t-transparent animate-spin" />
              <span>2. Searching 384-d FastEmbed vectors in Qdrant Cloud...</span>
            </div>
            <div className="flex items-center gap-2 text-indigo-300">
              <div className="w-3.5 h-3.5 rounded-full border border-indigo-400 border-t-transparent animate-spin" />
              <span>3. Specialist 1: Fact Finder Agent (6acd9f07...) extracting verified facts</span>
            </div>
            <div className="flex items-center gap-2 text-indigo-300">
              <Clock className="w-3.5 h-3.5" />
              <span>4. Specialist 2: Verifiable Data Analyst (6acd1ec7...) structuring action items</span>
            </div>
            <div className="flex items-center gap-2 text-slate-500">
              <Clock className="w-3.5 h-3.5" />
              <span>5. Manager Agent (6acdcd0f...): Coordinated synthesis and final answer</span>
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="glass-panel rounded-2xl p-5 border border-rose-800 bg-rose-950/40 text-rose-200 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold text-rose-300">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            Reasoning Workflow Failed
          </div>
          <p className="font-mono">{error}</p>
        </div>
      )}

      {/* Answer & Citations Card */}
      {response && !loading && (
        <div className="space-y-6 animate-fadeIn">
          {/* Main Answer */}
          <div className="glass-panel rounded-2xl p-6 sm:p-8 border border-sky-500/30 shadow-2xl space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-800/80">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center text-emerald-400">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Synthesized Agent Answer</h3>
                  <p className="text-[11px] text-slate-400 font-mono">Agent: {response.agent_id || 'AgentMemory Manager'}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {response.session_id && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    Session: {response.session_id.slice(0, 14)}...
                  </span>
                )}
                <button
                  onClick={onNavigateToExecution}
                  className="inline-flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300 font-medium"
                >
                  Inspect Execution
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="prose prose-invert max-w-none text-slate-100 text-sm leading-relaxed whitespace-pre-wrap font-sans">
              {response.answer}
            </div>
          </div>

          {/* Specialist Agent Intermediate Contributions */}
          {response.specialist_outputs && Object.keys(response.specialist_outputs).length > 0 && (
            <div className="glass-panel rounded-2xl p-6 border border-indigo-500/30 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Brain className="w-4 h-4 text-indigo-400" />
                  Specialist Agent Contributions (Multi-Agent Pipeline)
                </h3>
                <span className="text-[11px] text-indigo-400 font-mono">Coordinated by Manager Agent</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {response.specialist_outputs.fact_finder && (
                  <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-sky-300 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-sky-400" />
                        Fact Finder Agent (6acd9f07...)
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">Specialist 1</span>
                    </div>
                    <div className="text-xs text-slate-300 whitespace-pre-wrap font-sans max-h-48 overflow-y-auto leading-relaxed pr-1">
                      {response.specialist_outputs.fact_finder}
                    </div>
                  </div>
                )}

                {response.specialist_outputs.data_analyst && (
                  <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-purple-300 flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-purple-400" />
                        Verifiable Data Analyst (6acd1ec7...)
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">Specialist 2</span>
                    </div>
                    <div className="text-xs text-slate-300 whitespace-pre-wrap font-sans max-h-48 overflow-y-auto leading-relaxed pr-1">
                      {response.specialist_outputs.data_analyst}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Supporting Memories (Citations) */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                Ground Truth Citations ({response.supporting_memories?.length || 0})
              </h3>
              <span className="text-[11px] text-slate-400">Retrieved from Qdrant Cloud</span>
            </div>

            {!response.supporting_memories || response.supporting_memories.length === 0 ? (
              <p className="text-xs text-slate-400 italic">
                No supporting memories were retrieved above the similarity threshold.
              </p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {response.supporting_memories.map((mem, i) => (
                  <div
                    key={mem.id || i}
                    className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 text-xs space-y-2 hover:border-slate-700 transition-all"
                  >
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-mono text-sky-300 font-medium">
                        {mem.metadata?.speaker || (mem.metadata?.source === 'omi_conversation_summary' ? 'Summary' : 'Segment')}
                      </span>
                      {mem.score !== null && mem.score !== undefined && (
                        <span className="font-mono text-emerald-400 bg-emerald-950/70 px-1.5 py-0.5 rounded border border-emerald-800/50">
                          Match: {(mem.score * 100).toFixed(1)}%
                        </span>
                      )}
                    </div>
                    <p className="text-slate-200 line-clamp-3 leading-relaxed">
                      {mem.display_text || mem.content}
                    </p>
                    {mem.display_text && mem.display_text !== mem.content && (
                      <p className="text-[10px] text-amber-300/80 italic font-mono truncate">
                        Spoken: "{mem.content}"
                      </p>
                    )}
                    <div className="text-[10px] text-slate-500 font-mono truncate">
                      ID: {mem.id}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
