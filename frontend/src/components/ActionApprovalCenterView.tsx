import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RotateCw,
  Check,
  X,
  Database,
  ExternalLink,
  ListTodo,
  Mail,
} from 'lucide-react';
import { api } from '../services/api';
import { StagedAction } from '../types';

interface ActionApprovalCenterViewProps {
  uid: string;
}

export const ActionApprovalCenterView: React.FC<ActionApprovalCenterViewProps> = ({ uid }) => {
  const [actions, setActions] = useState<StagedAction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchActions = async () => {
    if (!uid.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listActions(uid.trim());
      setActions(data);
    } catch (err: any) {
      console.error('Failed to list actions:', err);
      setError(err?.message || 'Failed to fetch staged actions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActions();
  }, [uid]);

  const handleApprove = async (actionId: string) => {
    setExecutingId(actionId);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await api.confirmAction(actionId, uid.trim());
      setSuccessMsg(`Action approved! Created & verified in Google integration. (Memory ID: ${res.memory_id?.slice(0, 8)}...)`);
      fetchActions();
    } catch (err: any) {
      console.error('Approval error:', err);
      setError(err?.message || 'Failed to execute action.');
    } finally {
      setExecutingId(null);
    }
  };

  const handleReject = async (actionId: string) => {
    setExecutingId(actionId);
    try {
      await api.rejectAction(actionId, uid.trim());
      fetchActions();
    } catch (err: any) {
      console.error('Rejection error:', err);
      setError(err?.message || 'Failed to reject action.');
    } finally {
      setExecutingId(null);
    }
  };

  const stagedList = actions.filter((a) => a.status === 'staged');
  const completedList = actions.filter((a) => a.status === 'completed');
  const rejectedList = actions.filter((a) => a.status === 'rejected');

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
            <ShieldCheck className="w-7 h-7 text-emerald-400" />
            Action Approval Center
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Review proposed operator actions before they modify your real Google Calendar or Tasks.
          </p>
        </div>
        <button
          onClick={fetchActions}
          disabled={loading}
          className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 text-xs font-medium flex items-center gap-2 self-start sm:self-auto transition-all"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Pending Actions */}
      <div className="space-y-4">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-400" />
          <span>Actions Awaiting Approval ({stagedList.length})</span>
        </h2>

        {stagedList.length === 0 ? (
          <div className="p-8 rounded-2xl border border-slate-800/80 bg-slate-900/40 text-center text-sm text-slate-400">
            No pending actions awaiting approval. Run the Daily Operator to generate new actions.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {stagedList.map((action) => {
              const isExecuting = executingId === action.action_id;
              return (
                <div
                  key={action.action_id}
                  className="rounded-xl border border-amber-500/30 bg-slate-900/80 p-5 space-y-3 flex flex-col justify-between shadow-lg"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                        {action.action_type === 'create_gmail_draft' && <Mail className="w-3 h-3 text-amber-400" />}
                        {action.action_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-[11px] font-mono text-slate-500">
                        Expires: {new Date(action.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <h3 className="text-base font-semibold text-white">{action.title}</h3>
                    <p className="text-xs text-slate-300">{action.description}</p>
                    
                    {action.parameters?.recipient_email && (
                      <div className="text-[11px] font-mono text-sky-300 bg-sky-950/40 px-2 py-1 rounded border border-sky-800/40">
                        To: {action.parameters.recipient_email}
                      </div>
                    )}

                    {action.parameters?.due && (
                      <div className="text-[11px] font-mono text-slate-400 bg-slate-950/80 px-2 py-1 rounded border border-slate-800">
                        Due: {new Date(action.parameters.due).toLocaleString()}
                      </div>
                    )}
                  </div>

                  <div className="pt-3 border-t border-slate-800/80 flex items-center gap-2">
                    <button
                      onClick={() => handleApprove(action.action_id)}
                      disabled={isExecuting}
                      className="flex-1 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
                    >
                      {isExecuting ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                      <span>Approve & Execute</span>
                    </button>
                    <button
                      onClick={() => handleReject(action.action_id)}
                      disabled={isExecuting}
                      className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center justify-center gap-1 transition-all disabled:opacity-50"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Completed & Verified Actions */}
      <div className="space-y-4 pt-4">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Completed & Verified History ({completedList.length})</span>
        </h2>

        {completedList.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {completedList.map((action) => {
              const displayUrl =
                action.execution_result?.data?.display_url ||
                action.execution_result?.display_url;

              return (
                <div
                  key={action.action_id}
                  className="rounded-xl border border-emerald-500/30 bg-emerald-950/15 p-4 space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-medium">
                      VERIFIED ({action.action_type.replace(/_/g, ' ')})
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">
                      {new Date(action.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-white">{action.title}</h4>
                  <p className="text-xs text-slate-400">{action.description}</p>
                  
                  <div className="pt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-emerald-400 font-mono">
                    <span className="flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      <span>Integration Verified</span>
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-1 text-sky-400">
                        <Database className="w-3 h-3" />
                        <span>In Qdrant Memory</span>
                      </span>
                      {displayUrl && (
                        <a
                          href={displayUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2 py-0.5 rounded bg-sky-600/30 border border-sky-500/40 hover:bg-sky-600/50 text-sky-300 text-[10px] flex items-center gap-1 transition-all"
                        >
                          <span>Open in Gmail</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
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
