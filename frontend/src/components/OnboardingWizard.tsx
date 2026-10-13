import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  CheckCircle2Icon,
  AlertCircleIcon,
  ArrowRightIcon,
  ArrowLeftIcon,
  CopyIcon,
  CheckIcon,
  SparklesIcon,
  DatabaseIcon,
  BotIcon,
  SendIcon,
  MicIcon,
  CalendarIcon,
  ExternalLinkIcon,
  ShieldCheckIcon,
} from 'lucide-react';

interface OnboardingWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onFinish?: () => void;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({
  isOpen,
  onClose,
  onFinish,
}) => {
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [copied, setCopied] = useState<boolean>(false);
  const [testing, setTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Form states
  const [qdrantUrl, setQdrantUrl] = useState('');
  const [qdrantApiKey, setQdrantApiKey] = useState('');
  const [qdrantCollection, setQdrantCollection] = useState('agentmemory_memories');
  const [useDefaultQdrant, setUseDefaultQdrant] = useState(true);

  const [lyzrApiKey, setLyzrApiKey] = useState('');
  const [useDefaultLyzr, setUseDefaultLyzr] = useState(true);

  const [botToken, setBotToken] = useState('');
  const [botUsername, setBotUsername] = useState('Ididhswkje_bot');

  if (!isOpen || !user) return null;

  const backendBase = api.getBaseUrl();
  const omiConversationUrl = `${backendBase}/omi/v2/${user.omi_webhook_token}/conversation`;
  const omiRealtimeUrl = `${backendBase}/omi/v2/${user.omi_webhook_token}/realtime`;
  const telegramPairLink = `https://t.me/${botUsername}?start=pair_${user.telegram_pair_code || user.omi_webhook_token.substring(0, 8)}`;

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTestIntegration = async (type: string) => {
    setTesting(true);
    setTestResult(null);
    try {
      if (type === 'qdrant' && !useDefaultQdrant && qdrantUrl && qdrantApiKey) {
        await api.saveIntegration('qdrant', {
          qdrant_url: qdrantUrl,
          qdrant_api_key: qdrantApiKey,
          qdrant_collection_name: qdrantCollection,
        });
      } else if (type === 'lyzr' && !useDefaultLyzr && lyzrApiKey) {
        await api.saveIntegration('lyzr', {
          lyzr_api_key: lyzrApiKey,
        });
      } else if (type === 'telegram' && botToken) {
        await api.saveIntegration('telegram', {
          telegram_bot_token: botToken,
          telegram_bot_username: botUsername,
        });
      }

      const res = await api.testIntegration(type);
      setTestResult({
        success: res.success,
        message: res.message || 'Connection verified successfully!',
      });
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err?.message || 'Connection test failed. Please verify credentials.',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveStep = async () => {
    setTestResult(null);
    if (currentStep === 1 && !useDefaultQdrant) {
      if (qdrantUrl && qdrantApiKey) {
        await api.saveIntegration('qdrant', {
          qdrant_url: qdrantUrl,
          qdrant_api_key: qdrantApiKey,
          qdrant_collection_name: qdrantCollection,
        });
      }
    } else if (currentStep === 2 && !useDefaultLyzr) {
      if (lyzrApiKey) {
        await api.saveIntegration('lyzr', {
          lyzr_api_key: lyzrApiKey,
        });
      }
    } else if (currentStep === 3) {
      if (botToken) {
        await api.saveIntegration('telegram', {
          telegram_bot_token: botToken,
          telegram_bot_username: botUsername,
        });
      }
    }

    if (currentStep < 5) {
      setCurrentStep(currentStep + 1);
    } else {
      if (onFinish) onFinish();
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-2xl bg-[#0b1324] border border-cyan-500/40 rounded-3xl shadow-2xl p-6 sm:p-8 flex flex-col max-h-[90vh] overflow-y-auto">
        {/* Step indicator */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-950 border border-cyan-500/50 flex items-center justify-center text-cyan-400 font-bold">
              {currentStep}
            </div>
            <div>
              <div className="text-xs text-cyan-400 font-mono uppercase tracking-wider">
                Step {currentStep} of 5
              </div>
              <h2 className="text-lg font-bold text-white">
                {currentStep === 1 && '1. Semantic Memory (Qdrant Cloud)'}
                {currentStep === 2 && '2. Lyzr Multi-Agent Triad'}
                {currentStep === 3 && '3. Telegram Notifications & Approvals'}
                {currentStep === 4 && '4. Omi Voice Webhook Integration'}
                {currentStep === 5 && '5. Google Calendar, Tasks & Gmail'}
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-slate-400 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700/60"
          >
            Skip Setup
          </button>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mb-6">
          <div
            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full transition-all duration-300"
            style={{ width: `${(currentStep / 5) * 100}%` }}
          />
        </div>

        {/* Test Result Toast */}
        {testResult && (
          <div
            className={`mb-4 p-3 rounded-xl border text-xs flex items-center gap-2.5 ${
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
            <div>{testResult.message}</div>
          </div>
        )}

        {/* STEP 1: QDRANT */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <p className="text-xs text-slate-300 leading-relaxed">
              LifeOS indexes all spoken memories into Qdrant Cloud with 384-dimensional FastEmbed vectors. Every query is cryptographically scoped to your user account (<span className="text-cyan-400 font-mono">{user.id}</span>).
            </p>

            <div className="p-4 rounded-2xl bg-cyan-950/30 border border-cyan-500/20 flex items-start gap-3">
              <ShieldCheckIcon className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
              <div className="text-xs text-slate-300">
                <span className="font-semibold text-white">Managed Cluster Enabled by Default:</span> You can use the high-speed managed Qdrant Cloud cluster with strict tenant isolation, or configure your own cluster below.
              </div>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id="defaultQdrant"
                checked={useDefaultQdrant}
                onChange={(e) => setUseDefaultQdrant(e.target.checked)}
                className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500"
              />
              <label htmlFor="defaultQdrant" className="text-xs text-slate-200 cursor-pointer">
                Use managed Qdrant Cloud cluster (Zero setup required)
              </label>
            </div>

            {!useDefaultQdrant && (
              <div className="space-y-3 pt-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Qdrant Cluster Endpoint URL</label>
                  <input
                    type="url"
                    value={qdrantUrl}
                    onChange={(e) => setQdrantUrl(e.target.value)}
                    placeholder="https://xyz-your-cluster.qdrant.tech:6333"
                    className="w-full px-3.5 py-2 bg-slate-900 border border-slate-700 rounded-xl text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Qdrant API Key</label>
                  <input
                    type="password"
                    value={qdrantApiKey}
                    onChange={(e) => setQdrantApiKey(e.target.value)}
                    placeholder="eyJhbGciOi..."
                    className="w-full px-3.5 py-2 bg-slate-900 border border-slate-700 rounded-xl text-xs text-white"
                  />
                </div>
              </div>
            )}

            <div className="pt-2">
              <button
                type="button"
                onClick={() => handleTestIntegration('qdrant')}
                disabled={testing}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-cyan-300 font-mono flex items-center gap-2"
              >
                <DatabaseIcon className="w-3.5 h-3.5" />
                <span>{testing ? 'Testing Connection...' : 'Test Qdrant Connectivity'}</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: LYZR */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <p className="text-xs text-slate-300 leading-relaxed">
              LifeOS coordinates the Lyzr Triad: <strong className="text-white">Manager Agent</strong> plans the day, <strong className="text-white">Fact Finder Agent</strong> resolves memory context, and <strong className="text-white">Data Analyst Agent</strong> prepares schedules and actions.
            </p>

            <div className="flex items-center gap-2 pt-2">
              <input
                type="checkbox"
                id="defaultLyzr"
                checked={useDefaultLyzr}
                onChange={(e) => setUseDefaultLyzr(e.target.checked)}
                className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500"
              />
              <label htmlFor="defaultLyzr" className="text-xs text-slate-200 cursor-pointer">
                Use managed Lyzr Triad agents (Default Hackathon configuration)
              </label>
            </div>

            {!useDefaultLyzr && (
              <div className="space-y-3 pt-2">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Custom Lyzr Studio API Key</label>
                  <input
                    type="password"
                    value={lyzrApiKey}
                    onChange={(e) => setLyzrApiKey(e.target.value)}
                    placeholder="lyzr-sk-..."
                    className="w-full px-3.5 py-2 bg-slate-900 border border-slate-700 rounded-xl text-xs text-white"
                  />
                </div>
              </div>
            )}

            <div className="pt-2">
              <button
                type="button"
                onClick={() => handleTestIntegration('lyzr')}
                disabled={testing}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-cyan-300 font-mono flex items-center gap-2"
              >
                <BotIcon className="w-3.5 h-3.5" />
                <span>{testing ? 'Testing...' : 'Verify Lyzr Orchestration'}</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: TELEGRAM */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <p className="text-xs text-slate-300 leading-relaxed">
              Telegram is the approval and notification channel for LifeOS. When sensitive actions (like Gmail drafts) require human review, you receive interactive inline buttons directly in Telegram.
            </p>

            <div className="p-4 rounded-2xl bg-cyan-950/40 border border-cyan-500/30 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white">Instant Bot Linking:</span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-900/60 text-cyan-300 border border-cyan-500/40">
                  Pair Code: {user.telegram_pair_code || 'ACTIVE'}
                </span>
              </div>
              <p className="text-xs text-slate-300">
                Click below to open Telegram and send <code className="text-cyan-300">/start</code> to pair your account automatically:
              </p>
              <a
                href={telegramPairLink}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-medium text-xs shadow hover:opacity-90 transition-opacity"
              >
                <SendIcon className="w-3.5 h-3.5" />
                <span>Open @{botUsername} in Telegram</span>
                <ExternalLinkIcon className="w-3.5 h-3.5" />
              </a>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={() => handleTestIntegration('telegram')}
                disabled={testing}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-cyan-300 font-mono flex items-center gap-2"
              >
                <SendIcon className="w-3.5 h-3.5" />
                <span>{testing ? 'Verifying...' : 'Verify Telegram Bot (@Ididhswkje_bot)'}</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 4: OMI */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <p className="text-xs text-slate-300 leading-relaxed">
              Configure your dedicated webhook in the Omi mobile application. Any voice conversation you finish will automatically trigger your personal LifeOS operator!
            </p>

            <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-2">
              <label className="block text-xs font-medium text-slate-300">
                Your Dedicated Omi Webhook URL:
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={omiConversationUrl}
                  className="w-full px-3.5 py-2 bg-black/40 border border-slate-700 rounded-xl text-xs text-cyan-300 font-mono select-all"
                />
                <button
                  type="button"
                  onClick={() => handleCopy(omiConversationUrl)}
                  className="px-3 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs flex items-center gap-1.5 shrink-0"
                >
                  {copied ? <CheckIcon className="w-4 h-4" /> : <CopyIcon className="w-4 h-4" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 text-xs space-y-2 text-slate-300">
              <div className="font-semibold text-white">How to setup in Omi Mobile App:</div>
              <ol className="list-decimal pl-4 space-y-1 text-slate-400">
                <li>Open Omi on iOS or Android.</li>
                <li>Tap <strong>Settings</strong> → <strong>Developer</strong> → <strong>Webhooks</strong>.</li>
                <li>Paste your webhook URL from above into the Conversation URL field.</li>
                <li>Ensure <strong>Send on session complete</strong> is enabled.</li>
                <li>Speak naturally to Omi — your live pipeline starts instantly!</li>
              </ol>
            </div>
          </div>
        )}

        {/* STEP 5: GOOGLE */}
        {currentStep === 5 && (
          <div className="space-y-4">
            <p className="text-xs text-slate-300 leading-relaxed">
              Google Calendar, Google Tasks, and Gmail operate seamlessly through Composio on Lyzr. LifeOS autonomously reads events, checks free time, and prepares Gmail drafts for your Telegram approval.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col items-center text-center">
                <CalendarIcon className="w-6 h-6 text-cyan-400 mb-2" />
                <span className="text-xs font-semibold text-white">Google Calendar</span>
                <span className="text-[10px] text-emerald-400 font-mono mt-1">● Connected</span>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col items-center text-center">
                <CheckCircle2Icon className="w-6 h-6 text-blue-400 mb-2" />
                <span className="text-xs font-semibold text-white">Google Tasks</span>
                <span className="text-[10px] text-emerald-400 font-mono mt-1">● Connected</span>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col items-center text-center">
                <BotIcon className="w-6 h-6 text-purple-400 mb-2" />
                <span className="text-xs font-semibold text-white">Gmail Drafts</span>
                <span className="text-[10px] text-emerald-400 font-mono mt-1">● Staged with Approval</span>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-emerald-950/30 border border-emerald-500/30 text-xs text-emerald-200">
              🎉 <strong>You're all set!</strong> Your multi-tenant LifeOS workspace is fully configured and ready for live voice interactions.
            </div>
          </div>
        )}

        {/* Footer Navigation Buttons */}
        <div className="flex items-center justify-between border-t border-slate-800 pt-5 mt-auto">
          {currentStep > 1 ? (
            <button
              type="button"
              onClick={() => setCurrentStep(currentStep - 1)}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1.5"
            >
              <ArrowLeftIcon className="w-3.5 h-3.5" />
              <span>Back</span>
            </button>
          ) : (
            <div />
          )}

          <button
            type="button"
            onClick={handleSaveStep}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-medium text-xs flex items-center gap-2 shadow-lg shadow-cyan-500/20"
          >
            <span>{currentStep === 5 ? 'Launch LifeOS Operator' : 'Save & Continue'}</span>
            <ArrowRightIcon className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
