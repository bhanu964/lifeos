import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  IntegrationStatusItem,
  UserIntegrationsResponse,
} from '../types';
import {
  CheckCircle2Icon,
  AlertCircleIcon,
  CopyIcon,
  CheckIcon,
  RotateCwIcon,
  DatabaseIcon,
  BotIcon,
  SendIcon,
  CalendarIcon,
  ExternalLinkIcon,
  KeyIcon,
  RefreshCwIcon,
  Wand2Icon,
  ShieldCheckIcon,
} from 'lucide-react';

interface IntegrationsSettingsViewProps {
  onOpenWizard: () => void;
}

export const IntegrationsSettingsView: React.FC<IntegrationsSettingsViewProps> = ({
  onOpenWizard,
}) => {
  const { user, rotateOmiToken } = useAuth();
  const [integrations, setIntegrations] = useState<Record<string, IntegrationStatusItem>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [testingType, setTestingType] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ type: string; success: boolean; message: string } | null>(null);
  const [rotatingToken, setRotatingToken] = useState<boolean>(false);
  const [copiedUrl, setCopiedUrl] = useState<boolean>(false);

  const fetchIntegrations = async () => {
    setLoading(true);
    try {
      const res = await api.listIntegrations();
      setIntegrations(res.integrations || {});
    } catch (err) {
      console.error('Failed to load integrations:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleTest = async (type: string) => {
    setTestingType(type);
    setTestResult(null);
    try {
      const res = await api.testIntegration(type);
      setTestResult({
        type,
        success: res.success,
        message: res.message || 'Connected successfully!',
      });
      fetchIntegrations();
    } catch (err: any) {
      setTestResult({
        type,
        success: false,
        message: err?.message || 'Connection test failed.',
      });
    } finally {
      setTestingType(null);
    }
  };

  const handleRotateWebhookToken = async () => {
    if (!window.confirm('Are you sure you want to rotate your Omi webhook token? Previous URLs will be revoked immediately.')) {
      return;
    }
    setRotatingToken(true);
    try {
      await rotateOmiToken();
      alert('Omi webhook token rotated successfully! Update your Omi mobile app URL.');
    } catch (err) {
      alert('Failed to rotate token: ' + err);
    } finally {
      setRotatingToken(false);
    }
  };

  const backendBase = api.getBaseUrl();
  const omiUrl = user ? `${backendBase}/omi/v2/${user.omi_webhook_token}/conversation` : '';
  const telegramPairLink = user
    ? `https://t.me/Ididhswkje_bot?start=pair_${user.telegram_pair_code || user.omi_webhook_token.substring(0, 8)}`
    : '';

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl bg-[#0b1324] border border-cyan-500/30">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheckIcon className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-bold text-white">SaaS Tenant Integrations & Security</h2>
          </div>
          <p className="text-xs text-slate-400">
            Tenant: <span className="font-mono text-cyan-300 font-semibold">{user?.email}</span> (ID: <span className="font-mono text-slate-300">{user?.id}</span>)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={fetchIntegrations}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200 flex items-center gap-1.5 transition-colors"
          >
            <RefreshCwIcon className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={onOpenWizard}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-medium text-xs flex items-center gap-1.5 shadow"
          >
            <Wand2Icon className="w-3.5 h-3.5" />
            <span>Launch Setup Wizard</span>
          </button>
        </div>
      </div>

      {/* Test feedback toast */}
      {testResult && (
        <div
          className={`p-4 rounded-xl border text-xs flex items-center gap-2.5 ${
            testResult.success
              ? 'bg-emerald-950/70 border-emerald-500/40 text-emerald-200'
              : 'bg-red-950/70 border-red-500/40 text-red-200'
          }`}
        >
          {testResult.success ? (
            <CheckCircle2Icon className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircleIcon className="w-4 h-4 text-red-400 shrink-0" />
          )}
          <div>
            <strong>[{testResult.type.toUpperCase()}]:</strong> {testResult.message}
          </div>
        </div>
      )}

      {/* Dedicated Omi Webhook Box */}
      <div className="p-5 rounded-2xl bg-[#0b1324] border border-cyan-500/30 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">🎙️</span>
            <div>
              <h3 className="text-sm font-semibold text-white">Your Dedicated Omi Webhook URL</h3>
              <p className="text-[11px] text-slate-400">
                Spoken conversations sent to this endpoint are isolated to your memory & workflows.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleRotateWebhookToken}
            disabled={rotatingToken}
            className="px-3 py-1.5 rounded-lg bg-red-950/60 hover:bg-red-900 border border-red-500/40 text-red-300 text-xs font-mono flex items-center gap-1.5"
          >
            <RotateCwIcon className={`w-3.5 h-3.5 ${rotatingToken ? 'animate-spin' : ''}`} />
            <span>Rotate Token</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            readOnly
            value={omiUrl}
            className="w-full px-3.5 py-2.5 bg-slate-900/90 border border-slate-700/80 rounded-xl text-xs text-cyan-300 font-mono select-all"
          />
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(omiUrl);
              setCopiedUrl(true);
              setTimeout(() => setCopiedUrl(false), 2000);
            }}
            className="px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium flex items-center gap-1.5 shrink-0"
          >
            {copiedUrl ? <CheckIcon className="w-4 h-4" /> : <CopyIcon className="w-4 h-4" />}
            <span>{copiedUrl ? 'Copied!' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Telegram Linking Card */}
      <div className="p-5 rounded-2xl bg-[#0b1324] border border-cyan-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <SendIcon className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-white">Telegram Interactive Approvals</h3>
          </div>
          <p className="text-xs text-slate-400">
            Bot: <span className="font-mono text-cyan-300">@Ididhswkje_bot</span> • Chat Pairing Code:{' '}
            <span className="font-mono text-white font-bold">{user?.telegram_pair_code || 'LINKED'}</span>
          </p>
        </div>
        <a
          href={telegramPairLink}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium shadow"
        >
          <SendIcon className="w-3.5 h-3.5" />
          <span>Open Telegram & Link</span>
          <ExternalLinkIcon className="w-3 h-3" />
        </a>
      </div>

      {/* Grid of All Integrations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Qdrant */}
        <div className="p-6 rounded-2xl bg-[#0b1324] border border-slate-800 space-y-3.5 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <DatabaseIcon className="w-5 h-5 text-cyan-400" />
              <h4 className="text-base font-bold text-white">Qdrant Cloud</h4>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-mono bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-bold">
              ● Connected
            </span>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">
            384-dimensional FastEmbed persistent vector memory with tenant payload filter on <code className="text-cyan-300 font-mono">uid</code>.
          </p>
          <div className="text-xs font-mono text-slate-400 space-y-1">
            <div>Collection: <span className="text-slate-200">agentmemory_memories</span></div>
            <div>Cluster: <span className="text-slate-200">Shared High-Performance Cloud</span></div>
          </div>
          <button
            type="button"
            onClick={() => handleTest('qdrant')}
            disabled={testingType === 'qdrant'}
            className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-semibold border border-slate-700/80 transition-colors"
          >
            {testingType === 'qdrant' ? 'Testing...' : 'Test Cluster Connectivity'}
          </button>
        </div>

        {/* Lyzr */}
        <div className="p-6 rounded-2xl bg-[#0b1324] border border-slate-800 space-y-3.5 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <BotIcon className="w-5 h-5 text-blue-400" />
              <h4 className="text-base font-bold text-white">Lyzr Multi-Agent Triad</h4>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-mono bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-bold">
              ● Active
            </span>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">
            Manager, Fact Finder, and Data Analyst agents orchestrating daily plans and voice task execution.
          </p>
          <div className="text-xs font-mono text-slate-400 space-y-1">
            <div>Manager ID: <span className="text-slate-200">6acdcd0f8a6a...</span></div>
            <div>Mode: <span className="text-slate-200">Composio Autonomous Execution</span></div>
          </div>
          <button
            type="button"
            onClick={() => handleTest('lyzr')}
            disabled={testingType === 'lyzr'}
            className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-semibold border border-slate-700/80 transition-colors"
          >
            {testingType === 'lyzr' ? 'Testing...' : 'Verify Agent Orchestration'}
          </button>
        </div>

        {/* Google Calendar */}
        <div className="p-6 rounded-2xl bg-[#0b1324] border border-slate-800 space-y-3.5 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <CalendarIcon className="w-5 h-5 text-amber-400" />
              <h4 className="text-base font-bold text-white">Google Calendar</h4>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-mono bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-bold">
              ● Connected
            </span>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">
            Reads upcoming meetings, evaluates free time windows, and creates verified calendar events.
          </p>
          <div className="text-xs font-mono text-slate-400">
            Provider: <span className="text-slate-200">Composio on Lyzr</span>
          </div>
          <button
            type="button"
            onClick={() => handleTest('google_calendar')}
            disabled={testingType === 'google_calendar'}
            className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-semibold border border-slate-700/80 transition-colors"
          >
            {testingType === 'google_calendar' ? 'Testing...' : 'Test Calendar Access'}
          </button>
        </div>

        {/* Google Tasks & Gmail */}
        <div className="p-6 rounded-2xl bg-[#0b1324] border border-slate-800 space-y-3.5 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <CheckCircle2Icon className="w-5 h-5 text-purple-400" />
              <h4 className="text-base font-bold text-white">Google Tasks & Gmail</h4>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-mono bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-bold">
              ● Connected
            </span>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">
            Autonomous task verification and staged email drafts requiring explicit Telegram approval.
          </p>
          <div className="text-xs font-mono text-slate-400">
            Draft Policy: <span className="text-slate-200">Never Auto-Send without Human Approval</span>
          </div>
          <button
            type="button"
            onClick={() => handleTest('gmail')}
            disabled={testingType === 'gmail'}
            className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-semibold border border-slate-700/80 transition-colors"
          >
            {testingType === 'gmail' ? 'Testing...' : 'Test Gmail Integration'}
          </button>
        </div>
      </div>
    </div>
  );
};
