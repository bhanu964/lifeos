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
    { id: 'pipeline', label: 'Live Pipeline' },
    { id: 'actions', label: 'Action Approvals' },
    { id: 'memories', label: 'Voice Memories' },
    { id: 'notifications', label: 'Telegram Logs' },
    { id: 'settings', label: 'Integrations & Setup' },
    { id: 'diagnostics', label: 'System Health' },
  ];

  const isHealthy = health?.status === 'healthy';

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/60 bg-[#060a14]/75 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-sky-600 via-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 ring-1 ring-white/10 shrink-0">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-xl sm:text-2xl tracking-tight bg-gradient-to-r from-white via-sky-100 to-sky-400 bg-clip-text text-transparent">
                  LifeOS
                </span>
                <span className="hidden sm:inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide bg-sky-950/80 text-sky-300 border border-sky-800/60">
                  Personal AI Operator
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 font-medium">Track 2: Collaborative Multi-Agent Workflows</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1.5 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800/80">
            {tabs.map((tab) => {
              const active = currentTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange(tab.id)}
                  className={`px-3.5 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                    active
                      ? 'bg-sky-600 text-white shadow-md shadow-sky-600/30'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/70'
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
                <div className="flex items-center bg-slate-900/90 border border-cyan-500/40 rounded-xl px-3 py-1.5 text-sm">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 mr-2 shrink-0 animate-pulse" />
                  <span className="text-slate-400 text-xs mr-1 hidden sm:inline">Tenant:</span>
                  <span className="font-semibold text-cyan-200 max-w-[140px] truncate" title={user.email}>
                    {user.email.split('@')[0]}
                  </span>
                </div>

                {/* Wizard Quick Trigger */}
                <button
                  onClick={onOpenWizard}
                  title="Open Integration Setup Wizard"
                  className="hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-950/70 hover:bg-cyan-900/70 border border-cyan-500/50 text-cyan-200 text-sm font-semibold transition-colors"
                >
                  <Wand2 className="w-4 h-4" />
                  <span>Setup</span>
                </button>

                {/* Logout Button */}
                <button
                  onClick={onLogout}
                  title="Sign out of LifeOS"
                  className="p-2 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-300 hover:text-rose-300 hover:border-rose-500/50 transition-colors"
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
      <div className="border-t border-slate-800/60 bg-slate-950/80 px-4 sm:px-6 lg:px-8 py-2">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-y-1.5 gap-x-5 text-xs sm:text-sm">
          <div className="flex items-center gap-5 flex-wrap">
            {/* FastAPI Status */}
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isHealthy ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-rose-500 animate-pulse'
                }`}
              />
              <span className="text-slate-300 font-medium">FastAPI:</span>
              <span className={isHealthy ? 'text-emerald-400 font-mono font-semibold' : 'text-rose-400 font-mono'}>
                {isHealthy ? 'Online' : 'Offline'}
              </span>
            </div>

            {/* Qdrant Status */}
            <div className="flex items-center gap-2">
              <Database className="w-3.5 h-3.5 text-sky-400" />
              <span className="text-slate-300 font-medium">Qdrant Cloud:</span>
              <span className={health?.integrations.qdrant_configured ? 'text-emerald-400 font-mono font-semibold' : 'text-amber-400 font-medium'}>
                {health?.integrations.qdrant_configured ? 'Connected (384-d)' : 'Unconfigured'}
              </span>
            </div>

            {/* Lyzr Status */}
            <div className="flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-slate-300 font-medium">Lyzr Agents:</span>
              <span className={health?.integrations.lyzr_configured ? 'text-emerald-400 font-mono font-semibold' : 'text-amber-400 font-medium'}>
                {health?.integrations.lyzr_configured ? 'Active' : 'Unconfigured'}
              </span>
            </div>

            {/* Google Calendar Status */}
            <div className="flex items-center gap-2">
              <Calendar className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-slate-300 font-medium">Calendar:</span>
              <span className="text-emerald-400 font-mono font-semibold">Connected</span>
            </div>

            {/* Google Tasks Status */}
            <div className="flex items-center gap-2">
              <ListTodo className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-300 font-medium">Tasks:</span>
              <span className="text-emerald-400 font-mono font-semibold">Connected</span>
            </div>

            {/* Gmail Status */}
            <div className="flex items-center gap-2">
              <Mail className="w-3.5 h-3.5 text-sky-400" />
              <span className="text-slate-300 font-medium">Gmail:</span>
              <span className="text-emerald-400 font-mono font-semibold">Connected</span>
            </div>

            {/* Telegram Status */}
            <div className="flex items-center gap-2">
              <Bell className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-slate-300 font-medium">Telegram:</span>
              <span className="text-emerald-400 font-mono font-semibold">@Ididhswkje_bot</span>
            </div>
          </div>

          <div className="text-slate-400 text-xs hidden sm:block font-mono">
            {health?.timestamp ? `Synced: ${new Date(health.timestamp).toLocaleTimeString()}` : 'Connecting...'}
          </div>
        </div>
      </div>
    </header>
  );
};
