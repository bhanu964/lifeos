import React, { useState } from 'react';
import { X, Plus, AlertCircle, Database } from 'lucide-react';
import { api } from '../services/api';

interface AddMemoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  uid: string;
  onSuccess: () => void;
}

export const AddMemoryModal: React.FC<AddMemoryModalProps> = ({
  isOpen,
  onClose,
  uid,
  onSuccess,
}) => {
  const [content, setContent] = useState('');
  const [speaker, setSpeaker] = useState('User');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    setSaving(true);
    setError(null);

    try {
      await api.createMemory({
        uid,
        content: content.trim(),
        metadata: {
          source: 'manual',
          speaker: speaker.trim() || 'User',
          created_by: 'dashboard_ui',
        },
      });
      setContent('');
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to store memory');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-lg rounded-2xl p-6 border border-slate-700/80 shadow-2xl space-y-5 bg-[#0b1220]/95">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-sky-400" />
            <h2 className="text-base font-bold text-white">Add Voice Memory Manually</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Speaker Name
            </label>
            <input
              type="text"
              value={speaker}
              onChange={(e) => setSpeaker(e.target.value)}
              placeholder="e.g. User, Mr, Speaker_0"
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60 font-sans"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Transcript / Memory Text
            </label>
            <textarea
              rows={4}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Enter spoken sentence or thought to vectorize and store in Qdrant Cloud..."
              className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500/60 font-sans resize-none"
              required
            />
          </div>

          <div className="text-[11px] text-slate-400 font-mono">
            Will be stored under UID: <span className="text-sky-300">{uid}</span>
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !content.trim()}
              className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-600/25 transition-all disabled:opacity-50"
            >
              <Plus className="w-3.5 h-3.5" />
              {saving ? 'Vectorizing...' : 'Store in Qdrant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
