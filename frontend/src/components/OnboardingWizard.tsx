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
  SettingsIcon,
  LockIcon,
  ListTodoIcon,
  MailIcon,
} from 'lucide-react';

interface OnboardingWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onFinish?: () => void;
  initialStep?: number;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({
  isOpen,
  onClose,
  onFinish,
  initialStep = 1,
}) => {
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState<number>(initialStep);
  const [copied, setCopied] = useState<boolean>(false);
  const [testing, setTesting] = useState<boolean>(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Form states
  const [qdrantUrl, setQdrantUrl] = useState('');
  const [qdrantApiKey, setQdrantApiKey] = useState('');
  const [qdrantCollection, setQdrantCollection] = useState('agentmemory_memories');
  const [useDefaultQdrant, setUseDefaultQdrant] = useState(false);

  const [lyzrApiKey, setLyzrApiKey] = useState('');
  const [lyzrManagerAgentId, setLyzrManagerAgentId] = useState('');
  const [useDefaultLyzr, setUseDefaultLyzr] = useState(true);

  const [botToken, setBotToken] = useState('');
  const [botUsername, setBotUsername] = useState('Ididhswkje_bot');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [useDefaultTelegram, setUseDefaultTelegram] = useState(true);

  const [googleCalendarConnected, setGoogleCalendarConnected] = useState(true);
  const [googleTasksConnected, setGoogleTasksConnected] = useState(true);
  const [gmailConnected, setGmailConnected] = useState(false);

  // Sync initialStep when opened
  useEffect(() => {
    if (initialStep && initialStep >= 1 && initialStep <= 5) {
      setCurrentStep(initialStep);
    }
  }, [initialStep, isOpen]);

  // Load existing credentials if previously saved
  useEffect(() => {
    if (!isOpen) return;
    const loadSaved = async () => {
      try {
        const res = await api.listIntegrations();
        const items = res.integrations || {};

        if (items.qdrant) {
          if (items.qdrant.masked_fields?.source === 'managed_cluster') {
            setUseDefaultQdrant(true);
          } else if (items.qdrant.status === 'connected') {
            setUseDefaultQdrant(false);
          }
        }
        if (items.lyzr && items.lyzr.masked_fields?.source === 'custom') {
          setUseDefaultLyzr(false);
        }
        if (items.telegram && items.telegram.masked_fields?.source === 'custom') {
          setUseDefaultTelegram(false);
          if (items.telegram.masked_fields?.telegram_bot_username) {
            setBotUsername(items.telegram.masked_fields.telegram_bot_username);
          }
        }
        if (items.google_calendar && items.google_calendar.status === 'connected') {
          setGoogleCalendarConnected(true);
        }
        if (items.google_tasks && items.google_tasks.status === 'connected') {
          setGoogleTasksConnected(true);
        }
        if (items.gmail && items.gmail.status === 'connected') {
          setGmailConnected(true);
        }
      } catch (err) {
        console.debug('Could not prefill integrations:', err);
      }
    };
    loadSaved();
  }, [isOpen]);

  if (!isOpen || !user) return null;

  const backendBase = api.getBaseUrl();
  const omiConversationUrl = `${backendBase}/omi/v2/${user.omi_webhook_token}/conversation`;
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
      if (type === 'qdrant') {
        if (useDefaultQdrant) {
          await api.saveIntegration('qdrant', { use_managed: true });
        } else if (qdrantUrl && qdrantApiKey) {
          await api.saveIntegration('qdrant', {
            qdrant_url: qdrantUrl,
            qdrant_api_key: qdrantApiKey,
            qdrant_collection_name: qdrantCollection || 'agentmemory_memories',
          });
        }
      } else if (type === 'lyzr' && !useDefaultLyzr && lyzrApiKey) {
        await api.saveIntegration('lyzr', {
          lyzr_api_key: lyzrApiKey,
          lyzr_manager_agent_id: lyzrManagerAgentId || undefined,
        });
      } else if (type === 'telegram') {
        if (!useDefaultTelegram && botToken) {
          await api.saveIntegration('telegram', {
            telegram_bot_token: botToken,
            telegram_bot_username: botUsername,
            telegram_chat_id: telegramChatId || undefined,
          });
        }
      } else if (type === 'google_tasks' || type === 'google_calendar' || type === 'gmail') {
        // Direct test against current mode (Preconfigured Lyzr or User's Own Lyzr)
      }

      const res = await api.testIntegration(type);
      setTestResult({
        success: res.success,
        message: res.message || 'Connection verified successfully!',
      });
      if (res.success) {
        if (type === 'google_calendar') setGoogleCalendarConnected(true);
        if (type === 'google_tasks') setGoogleTasksConnected(true);
        if (type === 'gmail') setGmailConnected(true);
      }
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
    try {
      if (currentStep === 1) {
        if (useDefaultQdrant) {
          await api.saveIntegration('qdrant', { use_managed: true });
        } else if (qdrantUrl && qdrantApiKey) {
          await api.saveIntegration('qdrant', {
            qdrant_url: qdrantUrl,
            qdrant_api_key: qdrantApiKey,
            qdrant_collection_name: qdrantCollection || 'agentmemory_memories',
          });
        }
      } else if (currentStep === 2) {
        if (!useDefaultLyzr && lyzrApiKey) {
          await api.saveIntegration('lyzr', {
            lyzr_api_key: lyzrApiKey,
            lyzr_manager_agent_id: lyzrManagerAgentId || undefined,
          });
          setGmailConnected(true);
        } else if (useDefaultLyzr) {
          try {
            await api.disconnectIntegration('lyzr');
          } catch {
            // ignore if not configured
          }
          setGmailConnected(false);
        }
      } else if (currentStep === 3) {
        if (!useDefaultTelegram && botToken) {
          await api.saveIntegration('telegram', {
            telegram_bot_token: botToken,
            telegram_bot_username: botUsername,
            telegram_chat_id: telegramChatId || undefined,
          });
        }
      }
      // Step 5 has no manual credentials; it activates the connected Google services
    } catch (err) {
      console.warn('Error saving step credentials:', err);
    }

    if (currentStep < 5) {
      setCurrentStep(currentStep + 1);
    } else {
      if (onFinish) onFinish();
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/85 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-3xl bg-[#090f1d] border border-cyan-500/40 rounded-3xl shadow-2xl p-6 sm:p-10 flex flex-col max-h-[92vh] overflow-y-auto">
        {/* Step indicator header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-5 mb-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-cyan-950 border border-cyan-500/50 flex items-center justify-center text-cyan-400 font-bold text-xl shadow-lg shadow-cyan-950/50">
              {currentStep}
            </div>
            <div>
              <div className="text-xs sm:text-sm text-cyan-400 font-mono uppercase tracking-wider font-semibold">
                Step {currentStep} of 5
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                {currentStep === 1 && '1. Semantic Memory (Qdrant Cloud)'}
                {currentStep === 2 && '2. Lyzr AI Multi-Agent Triad'}
                {currentStep === 3 && '3. Telegram Notifications & Approvals'}
                {currentStep === 4 && '4. Omi Voice Device Integration'}
                {currentStep === 5 && '5. Connected Google Integrations'}
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-slate-400 hover:text-white px-3.5 py-1.5 rounded-xl border border-slate-700/60 transition-colors"
          >
            Close
          </button>
        </div>

        {/* Minimal Progress Bar */}
        <div className="w-full bg-slate-800/80 h-2 rounded-full overflow-hidden mb-6">
          <div
            className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full transition-all duration-300 rounded-full"
            style={{ width: `${(currentStep / 5) * 100}%` }}
          />
        </div>

        {/* Test Result Toast */}
        {testResult && (
          <div
            className={`mb-6 p-4 rounded-2xl border text-sm flex items-start gap-3 ${
              testResult.success
                ? 'bg-emerald-950/80 border-emerald-500/50 text-emerald-200'
                : 'bg-red-950/80 border-red-500/50 text-red-200'
            }`}
          >
            {testResult.success ? (
              <CheckCircle2Icon className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertCircleIcon className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            )}
            <div className="font-medium leading-relaxed">{testResult.message}</div>
          </div>
        )}

        {/* STEP 1: QDRANT */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <p className="text-base text-slate-300 leading-relaxed">
              LifeOS uses Qdrant Cloud to index spoken conversations into 384-dimensional FastEmbed vector memories with sub-10ms semantic retrieval. Every memory is cryptographically isolated to your tenant account (<span className="text-cyan-400 font-mono font-semibold">{user.id}</span>).
            </p>

            <div className="flex items-center gap-3 pt-1">
              <input
                type="checkbox"
                id="defaultQdrant"
                checked={useDefaultQdrant}
                onChange={(e) => setUseDefaultQdrant(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500 cursor-pointer"
              />
              <label htmlFor="defaultQdrant" className="text-sm sm:text-base text-slate-200 cursor-pointer font-medium">
                Use managed Qdrant Cloud cluster (Recommended • Zero configuration)
              </label>
            </div>

            {useDefaultQdrant ? (
              <div className="p-5 rounded-2xl bg-cyan-950/40 border border-cyan-500/40 flex items-start gap-3.5">
                <ShieldCheckIcon className="w-6 h-6 text-cyan-400 shrink-0 mt-0.5" />
                <div className="text-sm sm:text-base text-slate-200 leading-relaxed">
                  <strong className="text-white">Managed Cluster Active:</strong> Your memories are stored in the managed high-performance cluster with strict per-tenant cryptographic isolation (<code className="text-cyan-300 font-mono">{user.id}</code>). Other users cannot access or view your memories.
                </div>
              </div>
            ) : (
              <div className="space-y-4 p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
                <div className="text-sm text-slate-300 font-medium">
                  Connect your dedicated Qdrant Cloud cluster. LifeOS will store vector embeddings directly in your private database.
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-200 mb-1.5">
                    Qdrant Cluster Endpoint URL
                  </label>
                  <input
                    type="url"
                    value={qdrantUrl}
                    onChange={(e) => setQdrantUrl(e.target.value)}
                    placeholder="https://xyz-your-cluster.qdrant.tech:6333"
                    className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-200 mb-1.5">
                    Qdrant API Key
                  </label>
                  <input
                    type="password"
                    value={qdrantApiKey}
                    onChange={(e) => setQdrantApiKey(e.target.value)}
                    placeholder="eyJhbGciOi..."
                    className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-200 mb-1.5">
                    Collection Name
                  </label>
                  <input
                    type="text"
                    value={qdrantCollection}
                    onChange={(e) => setQdrantCollection(e.target.value)}
                    placeholder="agentmemory_memories"
                    className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                  <p className="text-xs text-slate-400 mt-1">Default: agentmemory_memories (automatically initialized)</p>
                </div>
              </div>
            )}

            <div className="pt-2">
              <button
                type="button"
                onClick={() => handleTestIntegration('qdrant')}
                disabled={testing}
                className="px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm text-cyan-300 font-mono font-medium flex items-center gap-2.5 transition-colors"
              >
                <DatabaseIcon className="w-4 h-4" />
                <span>{testing ? 'Testing Connection...' : 'Test Qdrant Connectivity'}</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: LYZR */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <p className="text-base text-slate-300 leading-relaxed">
              LifeOS coordinates the <strong className="text-white">Lyzr Multi-Agent Triad</strong>: the <strong className="text-white">Manager Agent</strong> synthesizes the executive plan, the <strong className="text-white">Fact Finder Agent</strong> validates context against memory, and the <strong className="text-white">Data Analyst Agent</strong> prepares schedules and actions.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setUseDefaultLyzr(true)}
                className={`p-5 rounded-2xl border text-left transition-all flex flex-col justify-between ${
                  useDefaultLyzr
                    ? 'bg-cyan-950/40 border-cyan-500 shadow-lg shadow-cyan-950/50'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
                      Mode 1 (Default)
                    </span>
                    {useDefaultLyzr && (
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-cyan-950 border border-cyan-500/50 text-cyan-300 font-semibold">
                        Selected
                      </span>
                    )}
                  </div>
                  <h4 className="text-base font-bold text-white mb-1.5">Preconfigured Lyzr</h4>
                  <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                    Uses preconfigured Lyzr agents with Google Calendar and Tasks ready out of the box. Gmail is disabled for account privacy.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
                  Zero setup required • Calendar &amp; Tasks active • Gmail disabled
                </div>
              </button>

              <button
                type="button"
                onClick={() => setUseDefaultLyzr(false)}
                className={`p-5 rounded-2xl border text-left transition-all flex flex-col justify-between ${
                  !useDefaultLyzr
                    ? 'bg-cyan-950/40 border-cyan-500 shadow-lg shadow-cyan-950/50'
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono font-bold text-indigo-400 uppercase tracking-wider">
                      Mode 2 (BYO Keys)
                    </span>
                    {!useDefaultLyzr && (
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-indigo-950 border border-indigo-500/50 text-indigo-300 font-semibold">
                        Selected
                      </span>
                    )}
                  </div>
                  <h4 className="text-base font-bold text-white mb-1.5">User&apos;s Own Lyzr Credentials</h4>
                  <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                    Connect your own Lyzr Studio account. Unlocks Google Calendar, Google Tasks, and Gmail drafts with your own tools.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
                  Personal Lyzr API key • Full Calendar, Tasks &amp; Gmail
                </div>
              </button>
            </div>

            {!useDefaultLyzr && (
              <div className="space-y-4 p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
                <div>
                  <label className="block text-sm font-semibold text-slate-200 mb-1.5">
                    Your Lyzr Studio API Key
                  </label>
                  <input
                    type="password"
                    value={lyzrApiKey}
                    onChange={(e) => setLyzrApiKey(e.target.value)}
                    placeholder="lyzr-sk-..."
                    className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-200 mb-1.5">
                    Custom Manager Agent ID (Optional)
                  </label>
                  <input
                    type="text"
                    value={lyzrManagerAgentId}
                    onChange={(e) => setLyzrManagerAgentId(e.target.value)}
                    placeholder="6acdcd0f8a6a8741bd6df3df"
                    className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                  <p className="text-xs text-slate-400 mt-1">Leave empty to use the default LifeOS Manager Agent ID.</p>
                </div>
              </div>
            )}

            <div className="pt-2">
              <button
                type="button"
                onClick={() => handleTestIntegration('lyzr')}
                disabled={testing}
                className="px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm text-cyan-300 font-mono font-medium flex items-center gap-2.5 transition-colors"
              >
                <BotIcon className="w-4 h-4" />
                <span>{testing ? 'Verifying Agents...' : 'Verify Lyzr Agent Orchestration'}</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 3: TELEGRAM */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <p className="text-base text-slate-300 leading-relaxed">
              Telegram is the real-time notification and human-in-the-loop approval channel for LifeOS. When actions like drafting an email require review, you receive interactive inline buttons directly in Telegram.
            </p>

            <div className="flex items-center gap-3 pt-1">
              <input
                type="checkbox"
                id="defaultTelegram"
                checked={useDefaultTelegram}
                onChange={(e) => {
                  setUseDefaultTelegram(e.target.checked);
                  if (e.target.checked) {
                    setBotUsername('Ididhswkje_bot');
                  }
                }}
                className="w-4 h-4 rounded border-slate-700 text-cyan-500 focus:ring-cyan-500 cursor-pointer"
              />
              <label htmlFor="defaultTelegram" className="text-sm sm:text-base text-slate-200 cursor-pointer font-medium">
                Use managed Telegram Bot (@Ididhswkje_bot)
              </label>
            </div>

            {useDefaultTelegram ? (
              <div className="p-5 rounded-2xl bg-cyan-950/40 border border-cyan-500/40 space-y-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                  <span className="text-sm sm:text-base font-semibold text-white">One-Click Bot Linking:</span>
                  <span className="text-xs sm:text-sm font-mono px-3 py-1 rounded-lg bg-cyan-900/80 text-cyan-300 border border-cyan-500/50">
                    Pair Code: {user.telegram_pair_code || 'ACTIVE'}
                  </span>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">
                  Click the button below to open Telegram and tap <strong className="text-cyan-300">Start</strong>. Your account pairs automatically with instant delivery!
                </p>
                <a
                  href={telegramPairLink}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold text-sm sm:text-base shadow-lg hover:opacity-95 transition-opacity"
                >
                  <SendIcon className="w-4 h-4" />
                  <span>Open @{botUsername} in Telegram</span>
                  <ExternalLinkIcon className="w-4 h-4" />
                </a>
              </div>
            ) : (
              <div className="space-y-4 p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
                <div>
                  <label className="block text-sm font-semibold text-slate-200 mb-1.5">
                    Your Telegram Bot Token (from @BotFather)
                  </label>
                  <input
                    type="password"
                    value={botToken}
                    onChange={(e) => setBotToken(e.target.value)}
                    placeholder="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ..."
                    className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-200 mb-1.5">
                    Your Telegram Bot Username
                  </label>
                  <input
                    type="text"
                    value={botUsername}
                    onChange={(e) => setBotUsername(e.target.value.replace(/^@/, ''))}
                    placeholder="MyLifeOS_bot"
                    className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-200 mb-1.5">
                    Your Telegram Chat ID (Optional)
                  </label>
                  <input
                    type="text"
                    value={telegramChatId}
                    onChange={(e) => setTelegramChatId(e.target.value)}
                    placeholder="987654321"
                    className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                  <p className="text-xs text-slate-400 mt-1">Optional. The bot will automatically discover your chat ID when you message /start.</p>
                </div>
              </div>
            )}

            <div className="pt-2">
              <button
                type="button"
                onClick={() => handleTestIntegration('telegram')}
                disabled={testing}
                className="px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm text-cyan-300 font-mono font-medium flex items-center gap-2.5 transition-colors"
              >
                <SendIcon className="w-4 h-4" />
                <span>
                  {testing
                    ? 'Verifying Bot...'
                    : `Verify Telegram Bot (@${botUsername || 'bot'})`}
                </span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 4: OMI */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <p className="text-base text-slate-300 leading-relaxed">
              Connect your physical <strong className="text-white">Omi device</strong> or the Omi app. Every conversation you have will automatically stream into LifeOS to trigger your personal agent operator!
            </p>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
              <label className="block text-sm font-semibold text-slate-200">
                Your Dedicated Omi Webhook URL:
              </label>
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
                <input
                  type="text"
                  readOnly
                  value={omiConversationUrl}
                  className="flex-1 px-4 py-3 bg-black/50 border border-slate-700 rounded-xl text-xs sm:text-sm text-cyan-300 font-mono select-all focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => handleCopy(omiConversationUrl)}
                  className="px-5 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold flex items-center justify-center gap-2 shrink-0 transition-colors"
                >
                  {copied ? <CheckIcon className="w-4 h-4" /> : <CopyIcon className="w-4 h-4" />}
                  <span>{copied ? 'Copied URL!' : 'Copy URL'}</span>
                </button>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800/80 text-sm space-y-3 text-slate-300">
              <div className="font-bold text-white text-base">Quick Omi Setup (Takes 30 seconds):</div>
              <ol className="list-decimal pl-5 space-y-2 text-slate-300 leading-relaxed">
                <li>Open the <strong>Omi App</strong> on your iPhone or Android.</li>
                <li>Tap <strong>Settings</strong> → <strong>Developer</strong> → <strong>Webhooks</strong>.</li>
                <li>Paste the webhook URL copied above into the <strong>Conversation URL</strong> field.</li>
                <li>Make sure <strong>Send on session complete</strong> is enabled.</li>
                <li>Speak naturally to Omi — your live pipeline starts automatically!</li>
              </ol>
            </div>
          </div>
        )}

        {/* STEP 5: GOOGLE */}
        {currentStep === 5 && (
          <div className="space-y-6">
            <p className="text-base text-slate-300 leading-relaxed">
              Google Workspace tools operate through Lyzr agent integrations. LifeOS offers two secure operating modes with strict isolation:
            </p>

            {useDefaultLyzr ? (
              <div className="space-y-6">
                {/* Mode 1 Header Card */}
                <div className="p-5 rounded-2xl bg-cyan-950/40 border border-cyan-500/40 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider">
                      Active Mode: Preconfigured Lyzr
                    </span>
                    <span className="px-3 py-1 rounded-full text-xs font-mono bg-cyan-950 border border-cyan-500/50 text-cyan-300 font-semibold">
                      Calendar &amp; Tasks Active
                    </span>
                  </div>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    You are using the LifeOS preconfigured Lyzr connection for <strong className="text-white">Google Calendar</strong> and <strong className="text-white">Google Tasks</strong> out of the box. Zero credential configuration is required.
                  </p>
                  <p className="text-xs text-amber-300/90 leading-relaxed pt-1">
                    To strictly protect developer privacy and prevent data exposure, <strong className="text-amber-200">Gmail is completely disabled and blocked</strong> on both the frontend and backend in this mode.
                  </p>
                </div>

                {/* Sub-services Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className={`p-4 rounded-2xl bg-slate-900 border flex flex-col items-center text-center ${googleCalendarConnected ? 'border-emerald-500/50' : 'border-slate-800'}`}>
                    <CalendarIcon className={`w-8 h-8 mb-2.5 ${googleCalendarConnected ? 'text-amber-400' : 'text-slate-500'}`} />
                    <span className="text-sm font-bold text-white">Google Calendar</span>
                    <span className="text-xs font-mono mt-1 font-semibold text-emerald-400">
                      Active (Preconfigured)
                    </span>
                  </div>
                  <div className={`p-4 rounded-2xl bg-slate-900 border flex flex-col items-center text-center ${googleTasksConnected ? 'border-emerald-500/50' : 'border-slate-800'}`}>
                    <ListTodoIcon className={`w-8 h-8 mb-2.5 ${googleTasksConnected ? 'text-blue-400' : 'text-slate-500'}`} />
                    <span className="text-sm font-bold text-white">Google Tasks</span>
                    <span className="text-xs font-mono mt-1 font-semibold text-emerald-400">
                      Active (Preconfigured)
                    </span>
                  </div>
                  <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col items-center text-center opacity-85">
                    <LockIcon className="w-8 h-8 mb-2.5 text-slate-500" />
                    <span className="text-sm font-bold text-slate-300">Gmail Drafts</span>
                    <span className="text-xs font-mono mt-1 font-semibold text-slate-400">
                      Disabled &amp; Inaccessible
                    </span>
                  </div>
                </div>

                {/* Test Action Buttons */}
                <div className="flex flex-wrap items-center gap-3 pt-1">
                  <button
                    type="button"
                    onClick={() => handleTestIntegration('google_calendar')}
                    disabled={testing}
                    className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                  >
                    <CalendarIcon className="w-4 h-4" />
                    <span>{testing ? 'Testing...' : 'Test Calendar Access'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTestIntegration('google_tasks')}
                    disabled={testing}
                    className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                  >
                    <ListTodoIcon className="w-4 h-4" />
                    <span>{testing ? 'Testing...' : 'Test Google Tasks'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setCurrentStep(2)}
                    className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-indigo-500/40 text-xs sm:text-sm text-indigo-300 font-medium flex items-center gap-2 transition-colors ml-auto"
                  >
                    <span>Need Gmail? Switch to User&apos;s Own Lyzr</span>
                    <ArrowRightIcon className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Mode 2 Header Card */}
                <div className="p-5 rounded-2xl bg-indigo-950/40 border border-indigo-500/40 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-indigo-400 uppercase tracking-wider">
                      Active Mode: User&apos;s Own Lyzr Credentials
                    </span>
                    <span className="px-3 py-1 rounded-full text-xs font-mono bg-indigo-950 border border-indigo-500/50 text-indigo-300 font-semibold">
                      Full Access Unlocked
                    </span>
                  </div>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    Google Calendar, Google Tasks, and Gmail operate strictly through <strong className="text-white">your own Lyzr Studio account</strong>. Tools execute with your permissions and will never touch or expose developer data.
                  </p>
                </div>

                {/* Sub-services Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className={`p-4 rounded-2xl bg-slate-900 border flex flex-col items-center text-center ${googleCalendarConnected ? 'border-emerald-500/50' : 'border-slate-800'}`}>
                    <CalendarIcon className={`w-8 h-8 mb-2.5 ${googleCalendarConnected ? 'text-amber-400' : 'text-slate-500'}`} />
                    <span className="text-sm font-bold text-white">Google Calendar</span>
                    <span className="text-xs font-mono mt-1 font-semibold text-emerald-400">
                      Connected (Your Tools)
                    </span>
                  </div>
                  <div className={`p-4 rounded-2xl bg-slate-900 border flex flex-col items-center text-center ${googleTasksConnected ? 'border-emerald-500/50' : 'border-slate-800'}`}>
                    <ListTodoIcon className={`w-8 h-8 mb-2.5 ${googleTasksConnected ? 'text-blue-400' : 'text-slate-500'}`} />
                    <span className="text-sm font-bold text-white">Google Tasks</span>
                    <span className="text-xs font-mono mt-1 font-semibold text-emerald-400">
                      Connected (Your Tools)
                    </span>
                  </div>
                  <div className={`p-4 rounded-2xl bg-slate-900 border flex flex-col items-center text-center ${gmailConnected ? 'border-emerald-500/50' : 'border-slate-800'}`}>
                    <MailIcon className={`w-8 h-8 mb-2.5 ${gmailConnected ? 'text-purple-400' : 'text-slate-500'}`} />
                    <span className="text-sm font-bold text-white">Gmail Drafts</span>
                    <span className="text-xs font-mono mt-1 font-semibold text-emerald-400">
                      Connected (HITL)
                    </span>
                  </div>
                </div>

                {/* Test Action Buttons */}
                <div className="flex flex-wrap items-center gap-3 pt-1">
                  <button
                    type="button"
                    onClick={() => handleTestIntegration('google_calendar')}
                    disabled={testing}
                    className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                  >
                    <CalendarIcon className="w-4 h-4" />
                    <span>{testing ? 'Testing...' : 'Test Calendar'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTestIntegration('google_tasks')}
                    disabled={testing}
                    className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                  >
                    <ListTodoIcon className="w-4 h-4" />
                    <span>{testing ? 'Testing...' : 'Test Tasks'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTestIntegration('gmail')}
                    disabled={testing}
                    className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs sm:text-sm text-cyan-300 font-mono font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                  >
                    <MailIcon className="w-4 h-4" />
                    <span>{testing ? 'Testing...' : 'Test Gmail'}</span>
                  </button>
                </div>
              </div>
            )}

            <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-xs sm:text-sm text-slate-300 flex items-start gap-3">
              <ShieldCheckIcon className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-white">Strict Isolation Enforced:</strong> Actions (such as creating events, reading emails, and writing drafts) only run against the authenticated user&apos;s own Google account and will never touch anyone else&apos;s data.
              </div>
            </div>
          </div>
        )}

        {/* Footer Navigation Buttons */}
        <div className="flex items-center justify-between border-t border-slate-800 pt-6 mt-8">
          {currentStep > 1 ? (
            <button
              type="button"
              onClick={() => setCurrentStep(currentStep - 1)}
              className="px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium flex items-center gap-2 transition-colors"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              <span>Back</span>
            </button>
          ) : (
            <div />
          )}

          <button
            type="button"
            onClick={handleSaveStep}
            className="px-7 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-sm sm:text-base flex items-center gap-2.5 shadow-lg shadow-cyan-500/25 transition-all"
          >
            <span>{currentStep === 5 ? 'Launch LifeOS Operator' : 'Save & Continue'}</span>
            <ArrowRightIcon className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};
