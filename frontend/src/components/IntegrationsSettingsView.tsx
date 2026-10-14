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
  SettingsIcon,
  SlidersIcon,
  RadioIcon,
  ServerIcon,
  CpuIcon,
  MailIcon,
  ListTodoIcon,
  Trash2Icon,
  AlertTriangleIcon,
} from 'lucide-react';

interface IntegrationsSettingsViewProps {
  onOpenWizard: (step?: number) => void;
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

  // Google credential management
  const [googleCredentialInput, setGoogleCredentialInput] = useState<string>('');
  const [savingGoogle, setSavingGoogle] = useState<boolean>(false);

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

  const handleSaveGoogle = async () => {
    if (!googleCredentialInput.trim()) return;
    setSavingGoogle(true);
    setTestResult(null);
    try {
      await api.saveIntegration('google_tasks', { credential_id: googleCredentialInput.trim() });
      await api.saveIntegration('google_calendar', { credential_id: googleCredentialInput.trim() });
      await api.saveIntegration('gmail', { credential_id: googleCredentialInput.trim() });

      const testRes = await api.testIntegration('google_tasks');
      setTestResult({
        type: 'google_workspace',
        success: testRes.success,
        message: 'Google Account connected and verified successfully!',
      });
      setGoogleCredentialInput('');
      fetchIntegrations();
    } catch (err: any) {
      setTestResult({
        type: 'google_workspace',
        success: false,
        message: err?.message || 'Failed to verify Google account credentials.',
      });
    } finally {
      setSavingGoogle(false);
    }
  };

  const handleDisconnectGoogle = async () => {
    if (!window.confirm('Disconnect your personal Google account? Tasks, calendar events, and email drafts will be paused until reconnected.')) {
      return;
    }
    try {
      await api.disconnectIntegration('google_tasks');
      await api.disconnectIntegration('google_calendar');
      await api.disconnectIntegration('gmail');
      setTestResult({
        type: 'google_workspace',
        success: true,
        message: 'Google account disconnected successfully.',
      });
      fetchIntegrations();
    } catch (err: any) {
      setTestResult({
        type: 'google_workspace',
        success: false,
        message: err?.message || 'Failed to disconnect Google account.',
      });
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
  const telegramBotUser = integrations.telegram?.masked_fields?.telegram_bot_username || 'Ididhswkje_bot';
  const telegramPairLink = user
    ? `https://t.me/${telegramBotUser}?start=pair_${user.telegram_pair_code || user.omi_webhook_token.substring(0, 8)}`
    : '';

  const isCustom = (type: string) => {
    return integrations[type]?.masked_fields?.source === 'custom';
  };

  const isGoogleConnected =
    integrations.google_tasks?.status === 'connected' ||
    integrations.google_calendar?.status === 'connected' ||
    integrations.gmail?.status === 'connected';

  const isTelegramConnected = integrations.telegram?.status === 'connected';
  const isQdrantConnected = integrations.qdrant?.status === 'connected';

  return (
    <div className="space-y-10 max-w-5xl mx-auto pb-12">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 p-6 sm:p-8 rounded-3xl bg-[#090f1d] border border-cyan-500/30 shadow-2xl">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheckIcon className="w-7 h-7 text-cyan-400" />
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">SaaS Tenant Integrations & Security</h2>
          </div>
          <p className="text-sm sm:text-base text-slate-300">
            Tenant: <span className="font-mono text-cyan-300 font-semibold">{user?.email}</span> (ID: <span className="font-mono text-slate-400">{user?.id}</span>)
          </p>
        </div>
        <div className="flex items-center gap-3.5">
          <button
            type="button"
            onClick={fetchIntegrations}
            disabled={loading}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm text-slate-200 flex items-center gap-2 transition-colors font-medium"
          >
            <RefreshCwIcon className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={() => onOpenWizard(1)}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-sm flex items-center gap-2 shadow-lg shadow-cyan-500/20 transition-all"
          >
            <Wand2Icon className="w-4 h-4" />
            <span>Setup Wizard</span>
          </button>
        </div>
      </div>

      {/* Test feedback toast */}
      {testResult && (
        <div
          className={`p-5 rounded-2xl border text-sm sm:text-base flex items-start gap-3.5 ${
            testResult.success
              ? 'bg-emerald-950/80 border-emerald-500/50 text-emerald-200'
              : 'bg-red-950/80 border-red-500/50 text-red-200'
          }`}
        >
          {testResult.success ? (
            <CheckCircle2Icon className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <AlertCircleIcon className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
          )}
          <div>
            <strong className="text-white">[{testResult.type.toUpperCase()}]:</strong> {testResult.message}
          </div>
        </div>
      )}

      {/* SECTION 1: LIFEOS MANAGED INFRASTRUCTURE */}
      <div className="space-y-5">
        <div className="border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5 text-cyan-400 mb-1">
            <ServerIcon className="w-5 h-5" />
            <span className="text-xs sm:text-sm font-mono uppercase tracking-wider font-bold">
              Infrastructure Pillar 1
            </span>
          </div>
          <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            LifeOS Managed Infrastructure
          </h3>
          <p className="text-sm sm:text-base text-slate-300 mt-1">
            Centrally operated execution engine, agent intelligence, and semantic memory. Strict cryptographic tenant isolation ensures user data is never shared across tenants.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Lyzr Triad */}
          <div className="p-6 sm:p-7 rounded-3xl bg-[#090f1d] border border-slate-800 space-y-4 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <BotIcon className="w-6 h-6 text-indigo-400" />
                  <h4 className="text-lg font-bold text-white">Lyzr Multi-Agent Triad</h4>
                </div>
                <div className="flex items-center gap-2">
                  {isCustom('lyzr') ? (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-cyan-950 border border-cyan-500/50 text-cyan-300 font-bold">
                      Custom Agent
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-slate-800 border border-slate-700 text-slate-400">
                      Managed Triad
                    </span>
                  )}
                  <span className="px-3 py-1 rounded-full text-xs font-mono bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-bold">
                    Active
                  </span>
                </div>
              </div>
              <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
                Manager, Fact Finder, and Data Analyst agents orchestrating daily plans and voice task execution.
              </p>
              <div className="text-xs sm:text-sm font-mono text-slate-400 space-y-1 mt-3">
                <div>Architecture: <span className="text-slate-200">Collaborative Multi-Agent Triad</span></div>
                <div>Runtime: <span className="text-slate-200">Lyzr Studio Cloud</span></div>
              </div>
            </div>
            <div className="flex items-center gap-3 pt-3">
              <button
                type="button"
                onClick={() => onOpenWizard(2)}
                className="flex-1 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm text-slate-200 font-medium border border-slate-700 transition-colors"
              >
                Configure Lyzr
              </button>
              <button
                type="button"
                onClick={() => handleTest('lyzr')}
                disabled={testingType === 'lyzr'}
                className="flex-1 py-3 rounded-xl bg-cyan-950 hover:bg-cyan-900 text-sm text-cyan-300 font-mono font-semibold border border-cyan-500/40 transition-colors"
              >
                {testingType === 'lyzr' ? 'Testing...' : 'Verify Agent'}
              </button>
            </div>
          </div>

          {/* Qdrant Cloud */}
          <div className="p-6 sm:p-7 rounded-3xl bg-[#090f1d] border border-slate-800 space-y-4 shadow-xl flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <DatabaseIcon className="w-6 h-6 text-cyan-400" />
                  <h4 className="text-lg font-bold text-white">Qdrant Semantic Memory</h4>
                </div>
                <div className="flex items-center gap-2">
                  {isCustom('qdrant') ? (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-cyan-950 border border-cyan-500/50 text-cyan-300 font-bold">
                      Custom Cluster
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-slate-800 border border-slate-700 text-slate-400">
                      Managed Cluster
                    </span>
                  )}
                  <span className={`px-3 py-1 rounded-full text-xs font-mono font-bold ${
                    isQdrantConnected
                      ? 'bg-emerald-950 border border-emerald-500/40 text-emerald-300'
                      : 'bg-amber-950 border border-amber-500/40 text-amber-300'
                  }`}>
                    {isQdrantConnected ? 'Connected' : 'Unconfigured'}
                  </span>
                </div>
              </div>
              <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
                384-dimensional FastEmbed vector memory with sub-10ms semantic retrieval filtered on <code className="text-cyan-300 font-mono">uid</code>.
              </p>
              <div className="text-xs sm:text-sm font-mono text-slate-400 space-y-1 mt-3">
                <div>Collection: <span className="text-slate-200">agentmemory_memories</span></div>
                <div>Isolation: <span className="text-cyan-300 font-mono">{user?.id}</span></div>
              </div>
            </div>
            <div className="flex items-center gap-3 pt-3">
              <button
                type="button"
                onClick={() => onOpenWizard(1)}
                className="flex-1 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm text-slate-200 font-medium border border-slate-700 transition-colors"
              >
                Configure Qdrant
              </button>
              <button
                type="button"
                onClick={() => handleTest('qdrant')}
                disabled={testingType === 'qdrant'}
                className="flex-1 py-3 rounded-xl bg-cyan-950 hover:bg-cyan-900 text-sm text-cyan-300 font-mono font-semibold border border-cyan-500/40 transition-colors"
              >
                {testingType === 'qdrant' ? 'Testing...' : 'Test Cluster'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 2: USER-OWNED PERSONAL INTEGRATIONS */}
      <div className="space-y-5">
        <div className="border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5 text-blue-400 mb-1">
            <KeyIcon className="w-5 h-5" />
            <span className="text-xs sm:text-sm font-mono uppercase tracking-wider font-bold">
              Infrastructure Pillar 2
            </span>
          </div>
          <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            User-Owned Personal Integrations
          </h3>
          <p className="text-sm sm:text-base text-slate-300 mt-1">
            Each user must explicitly connect their own personal accounts. LifeOS executes actions strictly against your account and never falls back to developer credentials. Unconfigured integrations are safely disabled.
          </p>
        </div>

        {/* Dedicated Omi Webhook Box */}
        <div className="p-6 sm:p-8 rounded-3xl bg-[#090f1d] border border-cyan-500/30 space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-2xl bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shrink-0 shadow-lg shadow-cyan-950">
                <RadioIcon className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h4 className="text-lg sm:text-xl font-bold text-white">Your Dedicated Omi Webhook URL</h4>
                  <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-950/80 border border-cyan-500/40 text-cyan-300">
                    Per-Tenant Isolation
                  </span>
                </div>
                <p className="text-sm text-slate-300 mt-1">
                  Spoken conversations captured by your Omi device stream directly into your personal pipeline.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => onOpenWizard(4)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs sm:text-sm text-slate-200 flex items-center gap-1.5 transition-colors font-medium"
              >
                <SlidersIcon className="w-3.5 h-3.5" />
                <span>Instructions</span>
              </button>
              <button
                type="button"
                onClick={handleRotateWebhookToken}
                disabled={rotatingToken}
                className="px-4 py-2 rounded-xl bg-red-950/60 hover:bg-red-900 border border-red-500/40 text-red-300 text-xs sm:text-sm font-mono flex items-center gap-1.5 transition-colors"
              >
                <RotateCwIcon className={`w-3.5 h-3.5 ${rotatingToken ? 'animate-spin' : ''}`} />
                <span>Rotate Token</span>
              </button>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-1">
            <input
              type="text"
              readOnly
              value={omiUrl}
              className="flex-1 px-4 py-3 bg-black/50 border border-slate-700 rounded-xl text-xs sm:text-sm text-cyan-300 font-mono select-all focus:outline-none"
            />
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(omiUrl);
                setCopiedUrl(true);
                setTimeout(() => setCopiedUrl(false), 2000);
              }}
              className="px-6 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold flex items-center justify-center gap-2 shrink-0 transition-colors"
            >
              {copiedUrl ? <CheckIcon className="w-4 h-4" /> : <CopyIcon className="w-4 h-4" />}
              <span>{copiedUrl ? 'Copied!' : 'Copy Webhook URL'}</span>
            </button>
          </div>
        </div>

        {/* Telegram Approvals Card */}
        <div className="p-6 sm:p-8 rounded-3xl bg-[#090f1d] border border-cyan-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 shadow-xl">
          <div>
            <div className="flex items-center gap-3 mb-1.5">
              <SendIcon className="w-5 h-5 text-blue-400" />
              <h4 className="text-lg sm:text-xl font-bold text-white">Telegram Notifications & Approvals</h4>
              <span className={`px-3 py-1 rounded-full text-xs font-mono font-semibold ${
                isTelegramConnected
                  ? 'bg-emerald-950 border border-emerald-500/40 text-emerald-300'
                  : 'bg-amber-950 border border-amber-500/40 text-amber-300'
              }`}>
                {isTelegramConnected ? 'Connected' : 'Action Required'}
              </span>
            </div>
            <p className="text-sm text-slate-300">
              Bot: <span className="font-mono text-cyan-300 font-semibold">@{telegramBotUser}</span> • Pairing Code:{' '}
              <span className="font-mono text-white font-bold">{user?.telegram_pair_code || 'LINKED'}</span>
            </p>
            {!isTelegramConnected && (
              <p className="text-xs text-amber-300 mt-1">
                Your Telegram account is not paired yet. Open the bot and send /start to receive notifications and approve actions.
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => onOpenWizard(3)}
              className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm text-slate-200 flex items-center gap-2 font-medium transition-colors"
            >
              <SettingsIcon className="w-4 h-4" />
              <span>Configure Bot</span>
            </button>
            <a
              href={telegramPairLink}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold shadow transition-colors"
            >
              <SendIcon className="w-4 h-4" />
              <span>Open in Telegram</span>
              <ExternalLinkIcon className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>

        {/* Google Workspace Account (Gmail, Google Tasks, Google Calendar) */}
        <div className="p-6 sm:p-8 rounded-3xl bg-[#090f1d] border border-cyan-500/30 space-y-6 shadow-xl">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1.5">
                <CalendarIcon className="w-6 h-6 text-amber-400" />
                <h4 className="text-lg sm:text-xl font-bold text-white">Google Workspace (Gmail, Tasks, Calendar)</h4>
                <span className={`px-3 py-1 rounded-full text-xs font-mono font-semibold ${
                  isGoogleConnected
                    ? 'bg-emerald-950 border border-emerald-500/40 text-emerald-300'
                    : 'bg-amber-950 border border-amber-500/40 text-amber-300'
                }`}>
                  {isGoogleConnected ? 'Connected' : 'Not Connected'}
                </span>
              </div>
              <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
                LifeOS reads calendar meetings, schedules tasks, and prepares staged email drafts strictly using <strong className="text-white">your personal Google account</strong>. Developer credentials are never used.
              </p>
            </div>
            {isGoogleConnected && (
              <button
                type="button"
                onClick={handleDisconnectGoogle}
                className="px-4 py-2 rounded-xl bg-red-950/60 hover:bg-red-900 border border-red-500/40 text-red-300 text-xs sm:text-sm font-mono flex items-center gap-1.5 transition-colors"
              >
                <Trash2Icon className="w-4 h-4" />
                <span>Disconnect Google</span>
              </button>
            )}
          </div>

          {/* Sub-services status grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className={`p-4 rounded-2xl bg-slate-900/90 border flex flex-col items-center text-center ${
              integrations.google_calendar?.status === 'connected' ? 'border-emerald-500/40' : 'border-slate-800'
            }`}>
              <CalendarIcon className={`w-7 h-7 mb-2 ${
                integrations.google_calendar?.status === 'connected' ? 'text-amber-400' : 'text-slate-500'
              }`} />
              <span className="text-sm font-bold text-white">Google Calendar</span>
              <span className={`text-xs font-mono mt-1 font-semibold ${
                integrations.google_calendar?.status === 'connected' ? 'text-emerald-400' : 'text-slate-400'
              }`}>
                {integrations.google_calendar?.status === 'connected' ? 'Connected' : 'Not Connected'}
              </span>
            </div>

            <div className={`p-4 rounded-2xl bg-slate-900/90 border flex flex-col items-center text-center ${
              integrations.google_tasks?.status === 'connected' ? 'border-emerald-500/40' : 'border-slate-800'
            }`}>
              <ListTodoIcon className={`w-7 h-7 mb-2 ${
                integrations.google_tasks?.status === 'connected' ? 'text-blue-400' : 'text-slate-500'
              }`} />
              <span className="text-sm font-bold text-white">Google Tasks</span>
              <span className={`text-xs font-mono mt-1 font-semibold ${
                integrations.google_tasks?.status === 'connected' ? 'text-emerald-400' : 'text-slate-400'
              }`}>
                {integrations.google_tasks?.status === 'connected' ? 'Connected' : 'Not Connected'}
              </span>
            </div>

            <div className={`p-4 rounded-2xl bg-slate-900/90 border flex flex-col items-center text-center ${
              integrations.gmail?.status === 'connected' ? 'border-emerald-500/40' : 'border-slate-800'
            }`}>
              <MailIcon className={`w-7 h-7 mb-2 ${
                integrations.gmail?.status === 'connected' ? 'text-purple-400' : 'text-slate-500'
              }`} />
              <span className="text-sm font-bold text-white">Gmail Drafts</span>
              <span className={`text-xs font-mono mt-1 font-semibold ${
                integrations.gmail?.status === 'connected' ? 'text-emerald-400' : 'text-slate-400'
              }`}>
                {integrations.gmail?.status === 'connected' ? 'Connected (HITL)' : 'Not Connected'}
              </span>
            </div>
          </div>

          {/* Connection input form */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-3">
            <label className="block text-sm font-semibold text-slate-200">
              Connect Google Account (OAuth / Composio Credential ID)
            </label>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <input
                type="text"
                value={googleCredentialInput}
                onChange={(e) => setGoogleCredentialInput(e.target.value)}
                placeholder="e.g. ca_user_google_oauth_..."
                className="flex-1 px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <button
                type="button"
                onClick={handleSaveGoogle}
                disabled={savingGoogle || !googleCredentialInput.trim()}
                className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-400 hover:to-cyan-400 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 transition-all shrink-0"
              >
                <CheckCircle2Icon className="w-4 h-4" />
                <span>{savingGoogle ? 'Verifying...' : 'Connect & Verify'}</span>
              </button>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              If left unconfigured, actions requiring Google services will be safely skipped or held in staging until connected.
            </p>
          </div>

          {/* Test buttons row */}
          {isGoogleConnected && (
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button
                type="button"
                onClick={() => handleTest('google_calendar')}
                disabled={testingType === 'google_calendar'}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-medium border border-slate-700 transition-colors"
              >
                {testingType === 'google_calendar' ? 'Testing...' : 'Test Calendar Access'}
              </button>
              <button
                type="button"
                onClick={() => handleTest('google_tasks')}
                disabled={testingType === 'google_tasks'}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-medium border border-slate-700 transition-colors"
              >
                {testingType === 'google_tasks' ? 'Testing...' : 'Test Google Tasks'}
              </button>
              <button
                type="button"
                onClick={() => handleTest('gmail')}
                disabled={testingType === 'gmail'}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-medium border border-slate-700 transition-colors"
              >
                {testingType === 'gmail' ? 'Testing...' : 'Test Gmail'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
