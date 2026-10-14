import React, { useState, useEffect } from 'react';
import {
  Send,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Bell,
  MessageSquare,
  ShieldCheck,
  ExternalLink,
  Info,
  Clock,
  Play,
} from 'lucide-react';
import { api } from '../services/api';
import { TelegramNotificationRecord } from '../types';

interface TelegramNotificationsViewProps {
  uid: string;
}

export const TelegramNotificationsView: React.FC<TelegramNotificationsViewProps> = ({ uid }) => {
  const [notifications, setNotifications] = useState<TelegramNotificationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Test notification runner state
  const [testMessage, setTestMessage] = useState('LifeOS Test: Google Task verified and completed.');
  const [testChatId, setTestChatId] = useState('');
  const [sendingTest, setSendingTest] = useState(false);
  const [testResult, setTestResult] = useState<TelegramNotificationRecord | null>(null);

  const fetchNotifications = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listNotifications(30);
      setNotifications(data);
    } catch (err: any) {
      console.error('Failed to fetch notifications:', err);
      setError(err?.message || 'Failed to load notifications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleSendTestNotification = async () => {
    if (!testMessage.trim()) return;
    setSendingTest(true);
    setError(null);
    setTestResult(null);

    try {
      const res = await api.testNotification(
        uid.trim(),
        testMessage.trim(),
        testChatId.trim() || undefined
      );
      setTestResult(res);
      fetchNotifications();
    } catch (err: any) {
      console.error('Test notification failed:', err);
      setError(err?.message || 'Failed to send test notification.');
    } finally {
      setSendingTest(false);
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="rounded-2xl border border-sky-500/20 bg-gradient-to-br from-slate-900/90 via-[#0a1428]/90 to-slate-900/90 p-6 md:p-8 backdrop-blur-xl shadow-2xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/20 text-sky-400 border border-sky-500/30">
                Operator Notifications
              </span>
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Post-Verification Only
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <Bell className="w-7 h-7 text-sky-400" />
              Telegram Operator Notifications
            </h1>
            <p className="text-sm md:text-base text-slate-400 max-w-2xl">
              LifeOS sends concise notifications only after underlying actions have actually succeeded and verified. Never notifies on planned or unconfirmed operations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchNotifications}
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 text-xs font-medium flex items-center gap-2 transition-all"
            >
              <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Log</span>
            </button>
          </div>
        </div>

        {/* Telegram Bot Card */}
        <div className="mt-6 p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-600/20 border border-sky-500/30 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-sky-400" />
            </div>
            <div>
              <div className="text-sm font-semibold text-white flex items-center gap-2">
                <span>Telegram Bot: @Ididhswkje_bot</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-mono">
                  Online
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Connected via Composio on Lyzr (Bot ID: 8364330229)
              </p>
            </div>
          </div>
          <a
            href="https://t.me/Ididhswkje_bot"
            target="_blank"
            rel="noreferrer"
            className="px-3.5 py-1.5 rounded-lg bg-sky-600/30 border border-sky-500/40 hover:bg-sky-600/40 text-sky-300 text-xs font-medium flex items-center gap-1.5 self-start sm:self-auto transition-all"
          >
            <span>Open @Ididhswkje_bot on Telegram</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      {/* Test Notification Interactive Box */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-md p-6 space-y-4">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Send className="w-4 h-4 text-sky-400" />
          <span>Test Notification Delivery</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="md:col-span-2 space-y-1">
            <label className="text-[11px] font-medium text-slate-400">Notification Message</label>
            <input
              type="text"
              value={testMessage}
              onChange={(e) => setTestMessage(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-sky-500 font-sans"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-slate-400">Target Chat ID (Optional)</label>
            <input
              type="text"
              value={testChatId}
              onChange={(e) => setTestChatId(e.target.value)}
              placeholder="E.g. numeric ID or leave blank"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
            />
          </div>
        </div>
        <div className="flex items-center justify-between pt-2">
          <p className="text-[11px] text-slate-500">
            Note: If no Chat ID is provided and no default is configured, the system marks the notification as <code className="text-amber-400 font-mono">skipped_no_chat_id</code>.
          </p>
          <button
            onClick={handleSendTestNotification}
            disabled={sendingTest || !testMessage.trim()}
            className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50"
          >
            {sendingTest ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-white" />}
            <span>Dispatch Test Notification</span>
          </button>
        </div>

        {testResult && (
          <div
            className={`p-3 rounded-lg border text-xs flex items-center gap-2 animate-fadeIn ${
              testResult.status === 'delivered'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : testResult.status === 'skipped_no_chat_id'
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}
          >
            {testResult.status === 'delivered' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <Info className="w-4 h-4 text-amber-400 shrink-0" />
            )}
            <span>
              Status: <strong>{testResult.status.toUpperCase()}</strong>. {testResult.error_message || 'Notification processed successfully.'}
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Notifications Log */}
      <div className="space-y-4">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <Clock className="w-4 h-4 text-slate-400" />
          <span>Real Notification Delivery Log ({notifications.length})</span>
        </h2>

        {notifications.length === 0 ? (
          <div className="p-8 rounded-2xl border border-slate-800/80 bg-slate-900/40 text-center text-sm text-slate-400">
            No notification events recorded yet. Approving a Google Task or Calendar event will automatically trigger verified delivery.
          </div>
        ) : (
          <div className="space-y-3">
            {notifications.map((notif) => {
              const isDelivered = notif.status === 'delivered';
              const isSkipped = notif.status === 'skipped_no_chat_id';

              return (
                <div
                  key={notif.notification_id}
                  className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2 hover:border-slate-700 transition-all"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase ${
                          isDelivered
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : isSkipped
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        }`}
                      >
                        {notif.status.replace(/_/g, ' ')}
                      </span>
                      <span className="text-sm font-semibold text-slate-200">
                        Event: {notif.event_type}
                      </span>
                      {notif.action_id && (
                        <span className="text-xs font-mono text-slate-400">
                          ({notif.action_id})
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-mono text-slate-400">
                      {new Date(notif.timestamp).toLocaleString()}
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 text-sm text-slate-100 whitespace-pre-wrap font-sans leading-relaxed">
                    {notif.text}
                  </div>

                  {notif.error_message && (
                    <div className="text-xs text-amber-400/90 font-mono">
                      Notice: {notif.error_message}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
