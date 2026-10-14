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
  const telegramBotUser = integrations.telegram?.masked_fields?.telegram_bot_username || 'Ididhswkje_bot';
  const telegramPairLink = user
    ? `https://t.me/${telegramBotUser}?start=pair_${user.telegram_pair_code || user.omi_webhook_token.substring(0, 8)}`
    : '';

  const isCustom = (type: string) => {
    return integrations[type]?.masked_fields?.source === 'custom';
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 p-6 sm:p-8 rounded-3xl bg-[#090f1d] border border-cyan-500/30 shadow-2xl">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheckIcon className="w-6 h-6 text-cyan-400" />
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

      {/* Dedicated Omi Webhook Box */}
      <div className="p-6 sm:p-8 rounded-3xl bg-[#090f1d] border border-cyan-500/30 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-2xl bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shrink-0 shadow-lg shadow-cyan-950">
              <RadioIcon className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-lg sm:text-xl font-bold text-white">Your Dedicated Omi Webhook URL</h3>
                <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-950/80 border border-cyan-500/40 text-cyan-300">
                  Per-Tenant Isolation
                </span>
              </div>
              <p className="text-sm text-slate-300 mt-1">
                Conversations captured by your Omi device trigger your personal multi-agent operator.
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

      {/* Telegram Linking Card */}
      <div className="p-6 sm:p-8 rounded-3xl bg-[#090f1d] border border-cyan-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 shadow-xl">
        <div>
          <div className="flex items-center gap-3 mb-1.5">
            <SendIcon className="w-5 h-5 text-blue-400" />
            <h3 className="text-lg sm:text-xl font-bold text-white">Telegram Interactive Approvals</h3>
            {isCustom('telegram') ? (
              <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-950 border border-cyan-500/50 text-cyan-300">
                Custom Bot
              </span>
            ) : (
              <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-slate-800 border border-slate-700 text-slate-300">
                Managed Bot
              </span>
            )}
          </div>
          <p className="text-sm text-slate-300">
            Bot: <span className="font-mono text-cyan-300 font-semibold">@{telegramBotUser}</span> • Chat Pairing Code:{' '}
            <span className="font-mono text-white font-bold">{user?.telegram_pair_code || 'LINKED'}</span>
          </p>
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

      {/* Grid of Core Integrations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Qdrant */}
        <div className="p-6 sm:p-7 rounded-3xl bg-[#090f1d] border border-slate-800 space-y-4 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <DatabaseIcon className="w-6 h-6 text-cyan-400" />
                <h4 className="text-lg font-bold text-white">Qdrant Cloud</h4>
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
                <span className="px-3 py-1 rounded-full text-xs font-mono bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-bold">
                  ● Connected
                </span>
              </div>
            </div>
            <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
              384-dimensional FastEmbed vector memory with sub-10ms semantic retrieval filtered on <code className="text-cyan-300 font-mono">uid</code>.
            </p>
            <div className="text-xs sm:text-sm font-mono text-slate-400 space-y-1 mt-3">
              <div>Collection: <span className="text-slate-200">agentmemory_memories</span></div>
              <div>Cluster: <span className="text-slate-200">{isCustom('qdrant') ? 'User Dedicated Cloud' : 'Managed High-Performance Pool'}</span></div>
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

        {/* Lyzr */}
        <div className="p-6 sm:p-7 rounded-3xl bg-[#090f1d] border border-slate-800 space-y-4 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <BotIcon className="w-6 h-6 text-blue-400" />
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
                  ● Active
                </span>
              </div>
            </div>
            <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
              Manager, Fact Finder, and Data Analyst agents orchestrating daily plans and voice task execution.
            </p>
            <div className="text-xs sm:text-sm font-mono text-slate-400 space-y-1 mt-3">
              <div>Manager ID: <span className="text-slate-200">6acdcd0f8a6a...</span></div>
              <div>Mode: <span className="text-slate-200">Composio Autonomous Execution</span></div>
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

        {/* Google Calendar */}
        <div className="p-6 sm:p-7 rounded-3xl bg-[#090f1d] border border-slate-800 space-y-4 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <CalendarIcon className="w-6 h-6 text-amber-400" />
                <h4 className="text-lg font-bold text-white">Google Calendar</h4>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-mono bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-bold">
                ● Connected
              </span>
            </div>
            <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
              Reads upcoming meetings, evaluates free time windows, and creates verified calendar events.
            </p>
            <div className="text-xs sm:text-sm font-mono text-slate-400 mt-3">
              Provider: <span className="text-slate-200">Composio on Lyzr</span>
            </div>
          </div>
          <div className="pt-3">
            <button
              type="button"
              onClick={() => handleTest('google_calendar')}
              disabled={testingType === 'google_calendar'}
              className="w-full py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm text-cyan-300 font-mono font-semibold border border-slate-700 transition-colors"
            >
              {testingType === 'google_calendar' ? 'Testing...' : 'Test Calendar Access'}
            </button>
          </div>
        </div>

        {/* Google Tasks & Gmail */}
        <div className="p-6 sm:p-7 rounded-3xl bg-[#090f1d] border border-slate-800 space-y-4 shadow-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <CheckCircle2Icon className="w-6 h-6 text-purple-400" />
                <h4 className="text-lg font-bold text-white">Google Tasks & Gmail</h4>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-mono bg-emerald-950 border border-emerald-500/40 text-emerald-300 font-bold">
                ● Connected
              </span>
            </div>
            <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
              Autonomous task creation and staged email drafts requiring explicit Telegram approval.
            </p>
            <div className="text-xs sm:text-sm font-mono text-slate-400 mt-3">
              Draft Policy: <span className="text-slate-200">Never Auto-Send without Human Approval</span>
            </div>
          </div>
          <div className="pt-3">
            <button
              type="button"
              onClick={() => handleTest('gmail')}
              disabled={testingType === 'gmail'}
              className="w-full py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm text-cyan-300 font-mono font-semibold border border-slate-700 transition-colors"
            >
              {testingType === 'gmail' ? 'Testing...' : 'Test Gmail Integration'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
