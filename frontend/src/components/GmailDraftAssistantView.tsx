import React, { useState } from 'react';
import {
  Mail,
  Send,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Edit3,
  Check,
  X,
  ExternalLink,
  Database,
  Brain,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { StagedAction } from '../types';

interface GmailDraftAssistantViewProps {
  uid: string;
}

const DEFAULT_DRAFT_PROMPT =
  'Draft an email to my project teammate explaining that the LifeOS demo is ready and asking them to review it tomorrow.';

export const GmailDraftAssistantView: React.FC<GmailDraftAssistantViewProps> = ({ uid }) => {
  const [prompt, setPrompt] = useState(DEFAULT_DRAFT_PROMPT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stagedDraft, setStagedDraft] = useState<StagedAction | null>(null);
  const [contextUsed, setContextUsed] = useState<string[]>([]);
  
  // Editable fields
  const [recipient, setRecipient] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  // Approval state
  const [isApproving, setIsApproving] = useState(false);
  const [approvalResult, setApprovalResult] = useState<any>(null);

  const handleGenerateDraft = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setApprovalResult(null);

    try {
      const res = await api.draftEmail({
        uid: uid.trim(),
        prompt: prompt.trim(),
      });
      setStagedDraft(res.staged_action);
      setContextUsed(res.context_used || []);
      setRecipient(res.staged_action.parameters?.recipient_email || 'teammate@lifeos.ai');
      setSubject(res.staged_action.parameters?.subject || 'Project Demo Ready for Review');
      setBody(res.staged_action.parameters?.body || '');
      setIsEditing(false);
    } catch (err: any) {
      console.error('Failed to generate draft:', err);
      setError(err?.message || 'Failed to generate email draft.');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveDraft = async () => {
    if (!stagedDraft) return;
    setIsApproving(true);
    setError(null);

    try {
      // If user modified fields, update parameters
      stagedDraft.parameters.recipient_email = recipient.trim();
      stagedDraft.parameters.subject = subject.trim();
      stagedDraft.parameters.body = body.trim();

      const res = await api.confirmAction(stagedDraft.action_id, uid.trim());
      setApprovalResult(res);
      setStagedDraft({
        ...stagedDraft,
        status: 'completed',
        verification_status: 'verified_live_integration',
        execution_result: res.execution_result,
      });
    } catch (err: any) {
      console.error('Draft approval failed:', err);
      setError(err?.message || 'Failed to create Gmail draft.');
    } finally {
      setIsApproving(false);
    }
  };

  const handleRejectDraft = async () => {
    if (!stagedDraft) return;
    try {
      await api.rejectAction(stagedDraft.action_id, uid.trim());
      setStagedDraft({
        ...stagedDraft,
        status: 'rejected',
      });
    } catch (err: any) {
      setError(err?.message || 'Failed to reject draft.');
    }
  };

  const displayUrl =
    stagedDraft?.execution_result?.data?.display_url ||
    stagedDraft?.execution_result?.display_url;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="rounded-2xl border border-sky-500/20 bg-gradient-to-br from-slate-900/90 via-[#0a1428]/90 to-slate-900/90 p-6 md:p-8 backdrop-blur-xl shadow-2xl relative overflow-hidden">
        <div className="relative z-10 space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/20 text-sky-400 border border-sky-500/30">
              Email Assistant
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
              <ShieldCheck className="w-3 h-3" /> Safe Staging: Drafts Only (Never Auto-Send)
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Mail className="w-7 h-7 text-sky-400" />
            Gmail Draft Assistant
          </h1>
          <p className="text-sm md:text-base text-slate-400 max-w-2xl">
            Synthesizes personal project context from Qdrant Cloud, drafts targeted emails via Lyzr agents, and stages drafts for your review and explicit approval.
          </p>
        </div>

        {/* Input box */}
        <div className="mt-6 space-y-3 relative z-10">
          <textarea
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="E.g. Draft an email to teammate asking to review the demo tomorrow..."
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-4 text-sm md:text-base text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500/80 transition-all resize-none font-sans"
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => setPrompt(DEFAULT_DRAFT_PROMPT)}
              className="text-xs text-sky-400 hover:text-sky-300 transition-colors underline underline-offset-2"
            >
              Reset to Teammate Demo Review Request
            </button>
            <button
              onClick={handleGenerateDraft}
              disabled={loading || !prompt.trim()}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-medium text-sm flex items-center gap-2 shadow-lg shadow-sky-500/25 transition-all disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Synthesizing Draft from Context...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Prepare Staged Draft</span>
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

        {approvalResult && (
          <div className="mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm flex items-center justify-between gap-3 animate-fadeIn">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
              <span>
                Gmail draft created & verified! Saved to Qdrant memory loop (Memory ID: {approvalResult.memory_id?.slice(0, 8)}...).
              </span>
            </div>
            {displayUrl && (
              <a
                href={displayUrl}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-all shrink-0"
              >
                <span>Open in Gmail</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        )}
      </div>

      {/* Staged Draft Card */}
      {stagedDraft && (
        <div className="rounded-2xl border border-sky-500/30 bg-slate-900/80 backdrop-blur-md p-6 md:p-8 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <Mail className="w-6 h-6 text-sky-400" />
              <div>
                <h2 className="text-lg font-bold text-white">Staged Email Draft</h2>
                <p className="text-xs text-slate-400">Action ID: {stagedDraft.action_id}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`text-xs px-2.5 py-1 rounded-full font-semibold ${
                  stagedDraft.status === 'completed'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : stagedDraft.status === 'rejected'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                    : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                }`}
              >
                {stagedDraft.status.toUpperCase()}
              </span>
              {stagedDraft.status === 'staged' && (
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1.5 transition-all"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>{isEditing ? 'Done Editing' : 'Edit Draft'}</span>
                </button>
              )}
            </div>
          </div>

          {/* Form / Content View */}
          <div className="space-y-4 text-sm">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                To (Recipient Email)
              </label>
              {isEditing ? (
                <input
                  type="email"
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white font-mono text-sm focus:outline-none focus:border-sky-500"
                />
              ) : (
                <div className="bg-slate-950/80 px-3 py-2 rounded-lg border border-slate-800 font-mono text-slate-200">
                  {recipient}
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Subject Line
              </label>
              {isEditing ? (
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white text-sm focus:outline-none focus:border-sky-500 font-medium"
                />
              ) : (
                <div className="bg-slate-950/80 px-3 py-2 rounded-lg border border-slate-800 text-white font-semibold">
                  {subject}
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Email Body
              </label>
              {isEditing ? (
                <textarea
                  rows={6}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-white text-sm focus:outline-none focus:border-sky-500 font-sans"
                />
              ) : (
                <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800 text-slate-200 whitespace-pre-wrap leading-relaxed font-sans text-sm">
                  {body}
                </div>
              )}
            </div>

            {/* Context used */}
            {contextUsed.length > 0 && (
              <div className="pt-2">
                <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mb-2">
                  <Database className="w-3.5 h-3.5 text-sky-400" />
                  Personal Context Retrieved from Qdrant:
                </span>
                <div className="space-y-1.5">
                  {contextUsed.map((ctx, idx) => (
                    <div
                      key={idx}
                      className="text-xs text-slate-400 bg-slate-950/40 border border-slate-800/80 px-3 py-2 rounded-lg font-mono"
                    >
                      {ctx}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          {stagedDraft.status === 'staged' && (
            <div className="pt-4 border-t border-slate-800 flex items-center gap-3">
              <button
                onClick={handleApproveDraft}
                disabled={isApproving}
                className="flex-1 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 transition-all disabled:opacity-50"
              >
                {isApproving ? (
                  <RotateCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Check className="w-4 h-4" />
                )}
                <span>Approve & Create Draft in Gmail</span>
              </button>
              <button
                onClick={handleRejectDraft}
                disabled={isApproving}
                className="py-3 px-5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-sm flex items-center gap-2 transition-all disabled:opacity-50"
              >
                <X className="w-4 h-4" />
                <span>Reject Draft</span>
              </button>
            </div>
          )}

          {stagedDraft.status === 'completed' && displayUrl && (
            <div className="pt-2 flex items-center justify-end">
              <a
                href={displayUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold transition-all shadow-md shadow-sky-600/20"
              >
                <span>View Draft in Google Mail</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
