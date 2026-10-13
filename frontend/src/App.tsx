import React, { useState, useEffect, useCallback } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Header } from './components/Header';
import { LandingPage } from './components/LandingPage';
import { AuthModal } from './components/AuthModal';
import { OnboardingWizard } from './components/OnboardingWizard';
import { IntegrationsSettingsView } from './components/IntegrationsSettingsView';
import { LivePipelineObservabilityView } from './components/LivePipelineObservabilityView';
import { DashboardView } from './components/DashboardView';
import { VoiceMemoriesView } from './components/VoiceMemoriesView';
import { ActionApprovalCenterView } from './components/ActionApprovalCenterView';
import { TelegramNotificationsView } from './components/TelegramNotificationsView';
import { AddMemoryModal } from './components/AddMemoryModal';
import Aurora from './components/reactbits/Aurora';
import { HealthResponse, MemoryItem, ExecutionEvent } from './types';
import { api } from './services/api';

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
  const [exploreDemoMode, setExploreDemoMode] = useState<boolean>(false);

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

      {/* Persistent App Header */}
      <Header
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        uid={uid}
        onUidChange={setUid}
        health={health}
        loadingHealth={loadingHealth}
        onRefresh={handleRefresh}
        defaultUid={DEFAULT_PHONE_UID}
        user={user}
        onOpenAuth={handleOpenAuth}
        onLogout={logout}
        onOpenWizard={() => setIsOnboardingOpen(true)}
      />

      {/* Missing Production API Config Banner */}
      {api.getConfigError() && (
        <div className="relative z-50 bg-amber-950/95 border-b border-amber-500/50 px-4 py-3 text-xs text-amber-200 shadow-lg">
          <div className="max-w-7xl mx-auto flex items-center gap-3">
            <span className="text-amber-400 text-sm">⚠️</span>
            <div>
              <strong className="text-amber-300">Vercel Environment Warning: </strong>
              <span>{api.getConfigError()}</span>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      {showLanding ? (
        <LandingPage
          onOpenAuth={handleOpenAuth}
          onExploreDemo={() => setExploreDemoMode(true)}
        />
      ) : (
        <main className="relative z-10 flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {currentTab === 'pipeline' && (
            <LivePipelineObservabilityView uid={uid} />
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
              onOpenWizard={() => setIsOnboardingOpen(true)}
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
      )}

      {/* Add Memory Modal */}
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
        onClose={() => setIsOnboardingOpen(false)}
        onFinish={() => {
          setIsOnboardingOpen(false);
          setCurrentTab('pipeline');
        }}
      />

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-800/60 bg-[#060a12]/80 backdrop-blur-md py-6 text-xs text-slate-500">
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
            <span>Google Calendar & Tasks</span>
            <span>•</span>
            <span>Omi Voice</span>
          </div>
        </div>
      </footer>
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
