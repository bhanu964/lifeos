import React, { useState } from 'react';
import {
  Brain,
  Database,
  Radio,
  Cpu,
  RefreshCw,
  User as UserIcon,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Calendar,
  ListTodo,
  Mail,
  Bell,
  LogOut,
  Wand2,
  LogIn,
  UserPlus,
  ShieldCheck,
} from 'lucide-react';
import { HealthResponse, User } from '../types';

interface HeaderProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  uid: string;
  onUidChange: (uid: string) => void;
  health: HealthResponse | null;
  loadingHealth: boolean;
  onRefresh: () => void;
  defaultUid: string;
  user: User | null;
  onOpenAuth: (mode: 'login' | 'signup') => void;
  onLogout: () => void;
  onOpenWizard: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onTabChange,
  uid,
  onUidChange,
  health,
  loadingHealth,
  onRefresh,
  defaultUid,
  user,
  onOpenAuth,
  onLogout,
  onOpenWizard,
}) => {
  const [editingUid, setEditingUid] = useState(false);
  const [tempUid, setTempUid] = useState(uid);

  const handleUidSave = () => {
    if (tempUid.trim()) {
      onUidChange(tempUid.trim());
    }
    setEditingUid(false);
  };

  const tabs = [
    { id: 'pipeline', label: '⚡ Live Pipeline' },
    { id: 'actions', label: 'Action Approvals' },
    { id: 'memories', label: 'Voice Memories' },
    { id: 'notifications', label: 'Telegram Logs' },
    { id: 'settings', label: '⚙️ Integrations & Setup' },
    { id: 'diagnostics', label: 'System Health' },
  ];

  const isHealthy = health?.status === 'healthy';

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/60 bg-[#060a14]/75 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 via-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 ring-1 ring-white/10">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-sky-100 to-sky-400 bg-clip-text text-transparent">
                  LifeOS
                </span>
                <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide bg-sky-950/80 text-sky-400 border border-sky-800/50">
                  Personal AI Operator
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium">Track 2: Collaborative Multi-Agent Workflows</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-800/60">
            {tabs.map((tab) => {
              const active = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                    active
                      ? 'bg-sky-600 text-white shadow-sm shadow-sky-600/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* User Account / Auth Actions */}
          <div className="flex items-center gap-2.5">
            {user ? (
              <div className="flex items-center gap-2">
                {/* User profile badge */}
                <div className="flex items-center bg-slate-900/90 border border-cyan-500/30 rounded-xl px-2.5 py-1 text-xs">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 mr-2 shrink-0 animate-pulse" />
                  <span className="text-slate-400 text-[11px] mr-1 hidden sm:inline">Tenant:</span>
                  <span className="font-medium text-cyan-200 max-w-[120px] truncate" title={user.email}>
                    {user.email.split('@')[0]}
                  </span>
                </div>

                {/* Wizard Quick Trigger */}
                <button
                  onClick={onOpenWizard}
                  title="Open Integration Setup Wizard"
                  className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/40 text-cyan-300 text-xs font-medium transition-colors"
                >
                  <Wand2 className="w-3.5 h-3.5" />
                  <span>Setup</span>
                </button>

                {/* Logout Button */}
                <button
                  onClick={onLogout}
                  title="Sign out of LifeOS"
                  className="p-1.5 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-400 hover:text-rose-300 hover:border-rose-500/40 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onOpenAuth('login')}
                  className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors"
                >
                  <LogIn className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Sign In</span>
                </button>
                <button
                  onClick={() => onOpenAuth('signup')}
                  className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-medium flex items-center gap-1.5 shadow shadow-cyan-500/20 transition-all"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  <span>Sign Up</span>
                </button>
              </div>
            )}

            {/* Refresh Button */}
            <button
              onClick={onRefresh}
              disabled={loadingHealth}
              title="Refresh integrations & pipeline"
              className="p-2 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingHealth ? 'animate-spin text-sky-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Mobile Navigation bar */}
        <div className="lg:hidden flex items-center gap-1 overflow-x-auto pb-2 pt-1 border-t border-slate-800/40">
          {tabs.map((tab) => {
            const active = currentTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  active
                    ? 'bg-sky-600 text-white'
                    : 'text-slate-400 hover:text-slate-200 bg-slate-900/40'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Integration Status Bar */}
      <div className="border-t border-slate-800/40 bg-slate-950/60 px-4 sm:px-6 lg:px-8 py-1.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-y-1 gap-x-4 text-[11px]">
          <div className="flex items-center gap-4 flex-wrap">
            {/* FastAPI Status */}
            <div className="flex items-center gap-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  isHealthy ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50' : 'bg-rose-500 animate-pulse'
                }`}
              />
              <span className="text-slate-400 font-medium">FastAPI Backend:</span>
              <span className={isHealthy ? 'text-emerald-400 font-mono' : 'text-rose-400 font-mono'}>
                {isHealthy ? 'Online (8000)' : 'Offline'}
              </span>
            </div>

            {/* Qdrant Status */}
            <div className="flex items-center gap-1.5">
              <Database className="w-3 h-3 text-sky-400" />
              <span className="text-slate-400">Qdrant Cloud:</span>
              <span className={health?.integrations.qdrant_configured ? 'text-emerald-400 font-mono' : 'text-amber-400'}>
                {health?.integrations.qdrant_configured ? 'Connected (384-d)' : 'Unconfigured'}
              </span>
            </div>

            {/* Lyzr Status */}
            <div className="flex items-center gap-1.5">
              <Cpu className="w-3 h-3 text-indigo-400" />
              <span className="text-slate-400">Lyzr Agents:</span>
              <span className={health?.integrations.lyzr_configured ? 'text-emerald-400 font-mono' : 'text-amber-400'}>
                {health?.integrations.lyzr_configured ? 'Active' : 'Unconfigured'}
              </span>
            </div>

            {/* Google Calendar Status */}
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3 h-3 text-blue-400" />
              <span className="text-slate-400">Google Calendar:</span>
              <span className="text-emerald-400 font-mono">Connected</span>
            </div>

            {/* Google Tasks Status */}
            <div className="flex items-center gap-1.5">
              <ListTodo className="w-3 h-3 text-emerald-400" />
              <span className="text-slate-400">Google Tasks:</span>
              <span className="text-emerald-400 font-mono">Connected</span>
            </div>

            {/* Gmail Status */}
            <div className="flex items-center gap-1.5">
              <Mail className="w-3 h-3 text-sky-400" />
              <span className="text-slate-400">Gmail:</span>
              <span className="text-emerald-400 font-mono">Connected (Drafts)</span>
            </div>

            {/* Telegram Status */}
            <div className="flex items-center gap-1.5">
              <Bell className="w-3 h-3 text-indigo-400" />
              <span className="text-slate-400">Telegram:</span>
              <span className="text-emerald-400 font-mono">@Ididhswkje_bot</span>
            </div>
          </div>

          <div className="text-slate-500 text-[10px] hidden sm:block">
            {health?.timestamp ? `Synced: ${new Date(health.timestamp).toLocaleTimeString()}` : 'Connecting...'}
          </div>
        </div>
      </div>
    </header>
  );
};
