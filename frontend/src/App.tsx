import React, { useState, useEffect, useCallback } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sidebar } from './components/Sidebar';
import { LandingPage } from './components/LandingPage';
import { AuthModal } from './components/AuthModal';
import { OnboardingWizard } from './components/OnboardingWizard';
import { IntegrationsSettingsView } from './components/IntegrationsSettingsView';
import { LivePipelineObservabilityView } from './components/LivePipelineObservabilityView';
import { ConversationActivityView } from './components/ConversationActivityView';
import { DashboardView } from './components/DashboardView';
import { VoiceMemoriesView } from './components/VoiceMemoriesView';
import { ActionApprovalCenterView } from './components/ActionApprovalCenterView';
import { TelegramNotificationsView } from './components/TelegramNotificationsView';
import { AddMemoryModal } from './components/AddMemoryModal';
import Aurora from './components/reactbits/Aurora';
import { HealthResponse, MemoryItem, ExecutionEvent } from './types';
import { api } from './services/api';
import { Menu, Wand2, RefreshCw } from 'lucide-react';

const DEFAULT_PHONE_UID = 'VFLpmF0dcuOCT4mzOEDtIKJG0H93';

function LifeOSDashboard() {
  const { user, logout } = useAuth();
  const [currentTab, setCurrentTab] = useState<string>('pipeline');
  const [uid, setUid] = useState<string>(user?.id || DEFAULT_PHONE_UID);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(false);
  const [loadingMemories, setLoadingMemories] = useState<boolean>(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [lastExecution, setLastExecution] = useState<ExecutionEvent[] | null>(null);

  // Modals & SaaS views
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('signup');
  const [isOnboardingOpen, setIsOnboardingOpen] = useState<boolean>(false);
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [exploreDemoMode, setExploreDemoMode] = useState<boolean>(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);

  // Keep uid synced when user changes
  useEffect(() => {
    if (user?.id) {
      setUid(user.id);
    }
  }, [user]);

  const fetchHealth = useCallback(async () => {
    setLoadingHealth(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      console.error('Failed to fetch backend health:', err);
      setHealth(null);
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  const fetchMemories = useCallback(async () => {
    if (!uid.trim()) return;
    setLoadingMemories(true);
    try {
      const data = await api.listMemories(uid.trim(), 100);
      setMemories(data);
    } catch (err) {
      console.error('Failed to list memories:', err);
      setMemories([]);
    } finally {
      setLoadingMemories(false);
    }
  }, [uid]);

  const handleRefresh = useCallback(() => {
    fetchHealth();
    fetchMemories();
  }, [fetchHealth, fetchMemories]);

  // Initial load
  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  const handleOpenAuth = (mode: 'login' | 'signup') => {
    setAuthMode(mode);
    setIsAuthModalOpen(true);
  };

  const showLanding = !user && !exploreDemoMode;

  return (
    <div
      className="relative min-h-screen text-slate-100 flex flex-col font-sans overflow-x-hidden"
      style={{ backgroundColor: '#080d16', minHeight: '100vh' }}
    >
      {/* Background Aurora */}
      <div
        className="fixed inset-0 pointer-events-none z-0 overflow-hidden"
        style={{
          width: '100vw',
          height: '100vh',
          position: 'fixed',
          top: 0,
          left: 0,
          backgroundColor: '#080d16',
          zIndex: 0,
        }}
        aria-hidden="true"
      >
        <Aurora
          colorStops={['#5227FF', '#7cff67', '#5227FF']}
          amplitude={1}
          blend={0.5}
          height={0.45}
          speed={1}
          glow={0.6}
        />
      </div>

      {showLanding ? (
        <LandingPage
          onOpenAuth={handleOpenAuth}
          onExploreDemo={() => setExploreDemoMode(true)}
        />
      ) : (
        <div className="relative z-10 flex min-h-screen">
          {/* Vertical Antigravity Sidebar */}
          <Sidebar
            currentTab={currentTab}
            onTabChange={setCurrentTab}
            uid={uid}
            onUidChange={setUid}
            health={health}
            loadingHealth={loadingHealth}
            onRefresh={handleRefresh}
            user={user}
            onOpenAuth={handleOpenAuth}
            onLogout={logout}
            onOpenWizard={() => {
              setWizardStep(1);
              setIsOnboardingOpen(true);
            }}
            onNewConversation={() => {
              setIsAddModalOpen(true);
            }}
            isMobileOpen={isMobileSidebarOpen}
            onCloseMobile={() => setIsMobileSidebarOpen(false)}
          />

          {/* Main Content Area (offset by sidebar width on lg) */}
          <div className="flex-1 flex flex-col min-w-0 lg:pl-80">
            {/* Minimal App Header with Mobile Hamburger & Navigation indicator */}
            <header className="sticky top-0 z-30 flex items-center justify-between px-4 sm:px-8 py-3.5 bg-[#060a14]/85 backdrop-blur-xl border-b border-slate-800/80">
              <div className="flex items-center gap-3.5">
                <button
                  type="button"
                  onClick={() => setIsMobileSidebarOpen(true)}
                  className="lg:hidden p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white"
                  aria-label="Open sidebar menu"
                >
                  <Menu className="w-5 h-5" />
                </button>
                <div>
                  <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight flex items-center gap-2">
                    {currentTab === 'pipeline' && '⚡ Live Pipeline'}
                    {currentTab === 'conversations' && '💬 Conversation History'}
                    {currentTab === 'actions' && '🛡️ Action Approval Center'}
                    {currentTab === 'memories' && '🧠 Voice Memories'}
                    {currentTab === 'notifications' && '📨 Telegram Logs & Delivery'}
                    {currentTab === 'settings' && '⚙️ Integrations & Settings'}
                    {currentTab === 'diagnostics' && '🩺 System Health & Diagnostics'}
                  </h1>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* Tenant pill */}
                {user && (
                  <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/90 border border-cyan-500/30 text-xs font-mono text-cyan-300">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>{user.email.split('@')[0]}</span>
                  </div>
                )}
                {/* Setup Wizard shortcut */}
                <button
                  type="button"
                  onClick={() => {
                    setWizardStep(1);
                    setIsOnboardingOpen(true);
                  }}
                  className="hidden sm:flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-cyan-950/70 hover:bg-cyan-900/70 border border-cyan-500/40 text-cyan-200 text-xs font-semibold transition-colors"
                >
                  <Wand2 className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Setup</span>
                </button>
                {/* Refresh */}
                <button
                  type="button"
                  onClick={handleRefresh}
                  disabled={loadingHealth}
                  title="Refresh pipeline & memory state"
                  className="p-2 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-400 hover:text-white transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${loadingHealth ? 'animate-spin text-cyan-400' : ''}`} />
                </button>
              </div>
            </header>

            {/* Missing Production API Config Banner */}
            {api.getConfigError() && (
              <div className="relative z-20 bg-amber-950/95 border-b border-amber-500/50 px-4 sm:px-8 py-3 text-xs text-amber-200 shadow-lg">
                <strong className="text-amber-300">Configuration Notice: </strong>
                <span>{api.getConfigError()}</span>
              </div>
            )}

            {/* Main Tab Content */}
            <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
              {currentTab === 'pipeline' && (
                <LivePipelineObservabilityView uid={uid} />
              )}

              {currentTab === 'conversations' && (
                <ConversationActivityView memories={memories} uid={uid} />
              )}

              {currentTab === 'actions' && (
                <ActionApprovalCenterView uid={uid} />
              )}

              {currentTab === 'memories' && (
                <VoiceMemoriesView
                  memories={memories}
                  loading={loadingMemories}
                  uid={uid}
                  onRefresh={fetchMemories}
                  onOpenAddModal={() => setIsAddModalOpen(true)}
                />
              )}

              {currentTab === 'notifications' && (
                <TelegramNotificationsView uid={uid} />
              )}

              {currentTab === 'settings' && (
                <IntegrationsSettingsView
                  onOpenWizard={(step?: number) => {
                    setWizardStep(step || 1);
                    setIsOnboardingOpen(true);
                  }}
                />
              )}

              {currentTab === 'diagnostics' && (
                <DashboardView
                  memories={memories}
                  health={health}
                  uid={uid}
                  onNavigate={setCurrentTab}
                  lastExecution={lastExecution}
                />
              )}
            </main>

            {/* Footer */}
            <footer className="border-t border-slate-800/60 bg-[#060a12]/80 backdrop-blur-md py-6 text-xs text-slate-500">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-300">LifeOS — Personal AI Operator</span>
                  <span>•</span>
                  <span>Stop Prompting, Solo Agents Hackathon 2026 (Track 2)</span>
                </div>
                <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
                  <span>FastAPI</span>
                  <span>•</span>
                  <span>Qdrant Cloud</span>
                  <span>•</span>
                  <span>Lyzr Multi-Agent</span>
                  <span>•</span>
                  <span>Omi Voice</span>
                </div>
              </div>
            </footer>
          </div>
        </div>
      )}

      {/* Add Memory / Spoken Voice Modal */}
      <AddMemoryModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        uid={uid}
        onSuccess={fetchMemories}
      />

      {/* SaaS Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        initialMode={authMode}
      />

      {/* SaaS Onboarding Wizard */}
      <OnboardingWizard
        isOpen={isOnboardingOpen}
        initialStep={wizardStep}
        onClose={() => setIsOnboardingOpen(false)}
        onFinish={() => {
          setIsOnboardingOpen(false);
          setCurrentTab('pipeline');
        }}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <LifeOSDashboard />
    </AuthProvider>
  );
}
