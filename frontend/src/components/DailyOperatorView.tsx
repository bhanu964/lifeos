import React, { useState, useEffect } from 'react';
import {
  Calendar,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Play,
  RotateCw,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Check,
  X,
  ExternalLink,
  Layers,
  ListTodo,
  Database,
  Brain,
} from 'lucide-react';
import { api } from '../services/api';
import {
  PlanResponse,
  StagedAction,
  ExecutionEvent,
} from '../types';

interface DailyOperatorViewProps {
  uid: string;
  onExecutionUpdate?: (events: ExecutionEvent[]) => void;
  onNavigateToExecution?: () => void;
}

const DEFAULT_PROMPT =
  'Plan my day for tomorrow. Check my calendar, identify suitable free time, and create tasks for finishing my hackathon demo and preparing my project presentation.';

export const DailyOperatorView: React.FC<DailyOperatorViewProps> = ({
  uid,
  onExecutionUpdate,
  onNavigateToExecution,
}) => {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [targetDate, setTargetDate] = useState('2026-10-14');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [executingActionId, setExecutingActionId] = useState<string | null>(null);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const handlePlanDay = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setActionSuccessMsg(null);

    try {
      const response = await api.planDay({
        uid: uid.trim(),
        prompt: prompt.trim(),
        target_date: targetDate,
      });
      setPlan(response);
      if (onExecutionUpdate && response.execution_events) {
        onExecutionUpdate(response.execution_events);
      }
    } catch (err: any) {
      console.error('Daily Operator planning error:', err);
      setError(err?.message || 'Failed to execute daily operator workflow.');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveAction = async (actionId: string) => {
    setExecutingActionId(actionId);
    setError(null);
    setActionSuccessMsg(null);

    try {
      const res = await api.confirmAction(actionId, uid.trim());
      setActionSuccessMsg(
        `Action approved! Successfully created and verified in Google integration. Stored to Qdrant memory (ID: ${res.memory_id?.slice(0, 8)}...).`
      );

      // Update local staged action status in plan
      if (plan) {
        const updated = plan.staged_actions.map((act) =>
          act.action_id === actionId
            ? {
                ...act,
                status: 'completed' as const,
                verification_status: 'verified_live_integration',
                execution_result: res.execution_result,
              }
            : act
        );
        setPlan({ ...plan, staged_actions: updated });
      }
    } catch (err: any) {
      console.error('Action approval error:', err);
      setError(err?.message || 'Failed to execute and verify action.');
    } finally {
      setExecutingActionId(null);
    }
  };

  const handleRejectAction = async (actionId: string) => {
    setExecutingActionId(actionId);
    try {
      await api.rejectAction(actionId, uid.trim());
      if (plan) {
        const updated = plan.staged_actions.map((act) =>
          act.action_id === actionId ? { ...act, status: 'rejected' as const } : act
        );
        setPlan({ ...plan, staged_actions: updated });
      }
    } catch (err: any) {
      console.error('Action rejection error:', err);
      setError(err?.message || 'Failed to reject action.');
    } finally {
      setExecutingActionId(null);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Hero Header */}
      <div className="rounded-2xl border border-sky-500/20 bg-gradient-to-br from-slate-900/90 via-[#0a1222]/90 to-slate-900/90 p-6 md:p-8 backdrop-blur-xl shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/20 text-sky-400 border border-sky-500/30">
                Track 2: Collaborative Multi-Agent Workflows
              </span>
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Real Integration Verified
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <Sparkles className="w-7 h-7 text-sky-400" />
              LifeOS Daily Operator
            </h1>
            <p className="text-sm md:text-base text-slate-400 max-w-2xl">
              Understand voice intent → Retrieve personal memory → Read real Google Calendar & Tasks → Plan focus blocks → Stage actions for human approval → Execute & verify live.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="w-full sm:w-auto">
              <label className="block text-[11px] font-medium text-slate-400 mb-1">Target Date</label>
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                className="bg-slate-950/80 border border-slate-700/80 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>
        </div>

        {/* Command Input Box */}
        <div className="mt-6 space-y-3 relative z-10">
          <div className="relative">
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Speak to Omi or type your daily operator instruction here..."
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-4 text-sm md:text-base text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500/80 transition-all resize-none font-sans"
            />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setPrompt(DEFAULT_PROMPT)}
              className="text-xs text-sky-400 hover:text-sky-300 transition-colors flex items-center gap-1 underline underline-offset-2"
            >
              Reset to Hackathon Demo Voice Request
            </button>
            <button
              onClick={handlePlanDay}
              disabled={loading || !prompt.trim()}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-medium text-sm flex items-center gap-2 shadow-lg shadow-sky-500/25 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Reading Calendar & Coordinating Agents...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  <span>Run LifeOS Operator</span>
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {actionSuccessMsg && (
          <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm flex items-center gap-3 animate-fadeIn">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
            <span>{actionSuccessMsg}</span>
          </div>
        )}
      </div>

      {/* Main Results Container */}
      {plan && (
        <div className="space-y-8 animate-fadeIn">
          {/* Executive Plan Summary Card */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-6 md:p-8 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <Brain className="w-6 h-6 text-sky-400" />
                <h2 className="text-lg font-semibold text-white">Lyzr Manager Executive Plan</h2>
              </div>
              <span className="text-xs font-mono text-slate-400">Target: {plan.target_date}</span>
            </div>
            <div className="prose prose-invert prose-sm max-w-none text-slate-300 leading-relaxed whitespace-pre-line font-sans">
              {plan.plan_summary}
            </div>
          </div>

          {/* Staged Actions — Human in the Loop Approval Center */}
          <div className="rounded-2xl border border-sky-500/30 bg-slate-900/70 backdrop-blur-md p-6 md:p-8 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-400" />
                  Staged Actions (Human-in-the-Loop Approval)
                </h2>
                <p className="text-xs text-slate-400">
                  LifeOS never executes external writes without explicit user approval. Approve to create verified Google items.
                </p>
              </div>
              <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-300 self-start sm:self-auto">
                {plan.staged_actions.filter((a) => a.status === 'staged').length} Actions Pending Approval
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {plan.staged_actions.map((action) => {
                const isExecuting = executingActionId === action.action_id;
                const isCompleted = action.status === 'completed';
                const isRejected = action.status === 'rejected';

                return (
                  <div
                    key={action.action_id}
                    className={`rounded-xl border p-5 flex flex-col justify-between transition-all ${
                      isCompleted
                        ? 'border-emerald-500/40 bg-emerald-950/20'
                        : isRejected
                        ? 'border-slate-800 bg-slate-950/40 opacity-60'
                        : 'border-slate-700 bg-slate-950/60 shadow-lg hover:border-sky-500/40'
                    }`}
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="px-2.5 py-0.5 rounded text-[11px] font-mono uppercase font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
                          {action.action_type.replace('_', ' ')}
                        </span>
                        <span
                          className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                            isCompleted
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : isRejected
                              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          }`}
                        >
                          {action.status.toUpperCase()}
                        </span>
                      </div>

                      <h3 className="text-base font-semibold text-white">{action.title}</h3>
                      <p className="text-xs text-slate-400 leading-relaxed">{action.description}</p>

                      {action.parameters?.due && (
                        <div className="text-[11px] font-mono text-slate-400 bg-slate-900/80 px-2 py-1 rounded border border-slate-800">
                          Due: {new Date(action.parameters.due).toLocaleString()}
                        </div>
                      )}

                      {isCompleted && (
                        <div className="mt-2 space-y-1.5 p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-300">
                          <div className="flex items-center gap-1.5 font-medium">
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                            <span>Verified in Google Tasks</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                            <Database className="w-3.5 h-3.5 text-sky-400" />
                            <span>Saved to Qdrant memory loop</span>
                          </div>
                        </div>
                      )}
                    </div>

                    {!isCompleted && !isRejected && (
                      <div className="mt-5 pt-3 border-t border-slate-800 flex items-center gap-2">
                        <button
                          onClick={() => handleApproveAction(action.action_id)}
                          disabled={isExecuting}
                          className="flex-1 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
                        >
                          {isExecuting ? (
                            <RotateCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Check className="w-3.5 h-3.5" />
                          )}
                          <span>Approve & Execute</span>
                        </button>
                        <button
                          onClick={() => handleRejectAction(action.action_id)}
                          disabled={isExecuting}
                          className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center justify-center gap-1 transition-all disabled:opacity-50"
                        >
                          <X className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Three-Column Operational Overview: Calendar, Focus Slots, Tasks */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Real Google Calendar Events */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-blue-400" />
                  <h3 className="font-semibold text-white text-sm">Google Calendar Events</h3>
                </div>
                <span className="text-xs font-mono text-slate-400">{plan.existing_events.length}</span>
              </div>
              {plan.existing_events.length === 0 ? (
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-center text-xs text-slate-400">
                  No conflicting events found for {plan.target_date}.
                </div>
              ) : (
                <div className="space-y-2">
                  {plan.existing_events.map((evt, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                      <div className="font-medium text-slate-200">{evt.summary}</div>
                      <div className="text-slate-400 text-[11px]">
                        {evt.start_time} - {evt.end_time}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Calculated Focus Slots */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Clock className="w-5 h-5 text-amber-400" />
                  <h3 className="font-semibold text-white text-sm">Suggested Focus Blocks</h3>
                </div>
                <span className="text-xs font-mono text-slate-400">{plan.suggested_slots.length}</span>
              </div>
              <div className="space-y-2">
                {plan.suggested_slots.map((slot, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                    <div className="font-medium text-amber-300">{slot.label}</div>
                    <div className="text-slate-400 text-[11px]">
                      {new Date(slot.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} –{' '}
                      {new Date(slot.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ({slot.duration_minutes} min)
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Google Tasks */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <ListTodo className="w-5 h-5 text-emerald-400" />
                  <h3 className="font-semibold text-white text-sm">Google Tasks</h3>
                </div>
                <span className="text-xs font-mono text-slate-400">{plan.pending_tasks.length}</span>
              </div>
              {plan.pending_tasks.length === 0 ? (
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-center text-xs text-slate-400">
                  No active pending tasks in primary list.
                </div>
              ) : (
                <div className="space-y-2">
                  {plan.pending_tasks.map((task, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                      <div className="font-medium text-slate-200">{task.title}</div>
                      {task.due && <div className="text-slate-400 text-[11px]">Due: {task.due}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Stepper Telemetry Link */}
          {onNavigateToExecution && (
            <div className="text-center pt-2">
              <button
                onClick={onNavigateToExecution}
                className="inline-flex items-center gap-2 text-xs font-medium text-sky-400 hover:text-sky-300 transition-colors"
              >
                <span>View Full Multi-Agent Execution Telemetry</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
