import React, { useState } from 'react';
import {
  Brain,
  Plus,
  Zap,
  MessageSquare,
  Database,
  ShieldCheck,
  Send,
  Settings,
  Activity,
  Calendar,
  ListTodo,
  Mail,
  Cpu,
  RefreshCw,
  LogOut,
  LogIn,
  UserPlus,
  Wand2,
  ChevronRight,
  Menu,
  X,
  ExternalLink,
} from 'lucide-react';
import { HealthResponse, User } from '../types';

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  uid: string;
  onUidChange: (uid: string) => void;
  health: HealthResponse | null;
  loadingHealth: boolean;
  onRefresh: () => void;
  user: User | null;
  onOpenAuth: (mode: 'login' | 'signup') => void;
  onLogout: () => void;
  onOpenWizard: () => void;
  onNewConversation: () => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  uid,
  health,
  loadingHealth,
  onRefresh,
  user,
  onOpenAuth,
  onLogout,
  onOpenWizard,
  onNewConversation,
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const isHealthy = health?.status === 'healthy';

  const navItems = [
    {
      id: 'pipeline',
      label: 'Live Pipeline',
      icon: Zap,
      badge: 'Active',
      badgeColor: 'bg-cyan-950 text-cyan-300 border-cyan-500/40',
    },
    {
      id: 'conversations',
      label: 'Conversation History',
      icon: MessageSquare,
    },
    {
      id: 'actions',
      label: 'Action Approvals',
      icon: ShieldCheck,
      badge: 'Telegram',
      badgeColor: 'bg-blue-950 text-blue-300 border-blue-500/40',
    },
    {
      id: 'memories',
      label: 'Voice Memories',
      icon: Database,
    },
    {
      id: 'notifications',
      label: 'Telegram Logs',
      icon: Send,
    },
    {
      id: 'settings',
      label: 'Integrations & Settings',
      icon: Settings,
      badge: 'BYO Keys',
      badgeColor: 'bg-purple-950 text-purple-300 border-purple-500/40',
    },
    {
      id: 'diagnostics',
      label: 'System Diagnostics',
      icon: Activity,
    },
  ];

  const handleNavClick = (tabId: string) => {
    onTabChange(tabId);
    if (onCloseMobile) {
      onCloseMobile();
    }
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm lg:hidden animate-fade-in"
          onClick={onCloseMobile}
        />
      )}

      {/* Vertical Sidebar */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-72 sm:w-80 bg-[#070c17]/95 border-r border-slate-800/80 backdrop-blur-2xl flex flex-col justify-between transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Top Header & Brand */}
        <div className="p-5 border-b border-slate-800/80">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-cyan-600 via-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/25 ring-1 ring-white/20 shrink-0">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-extrabold text-2xl tracking-tight bg-gradient-to-r from-white via-cyan-100 to-cyan-400 bg-clip-text text-transparent">
                    LifeOS
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                    2.0
                  </span>
                </div>
                <p className="text-xs text-slate-400 font-medium">Personal AI Operator</p>
              </div>
            </div>

            {/* Mobile close button */}
            {onCloseMobile && (
              <button
                type="button"
                onClick={onCloseMobile}
                className="lg:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>

          {/* Primary Action: New Conversation Button */}
          <div className="mt-5">
            <button
              type="button"
              onClick={() => {
                onNewConversation();
                if (onCloseMobile) onCloseMobile();
              }}
              className="w-full py-3 px-4 rounded-2xl bg-gradient-to-r from-cyan-500 via-sky-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-sm sm:text-base flex items-center justify-center gap-2.5 shadow-lg shadow-cyan-500/25 transition-all active:scale-[0.98]"
            >
              <Plus className="w-5 h-5 stroke-[2.5]" />
              <span>New Conversation</span>
            </button>
          </div>
        </div>

        {/* Middle Navigation & Status Area */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-6 scrollbar-thin scrollbar-thumb-slate-800">
          {/* Main Navigation List */}
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 px-3 mb-2 font-semibold">
              Workflows & History
            </div>
            <nav className="space-y-1.5">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = currentTab === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleNavClick(item.id)}
                    className={`w-full flex items-center justify-between px-3.5 py-3 rounded-2xl text-sm font-semibold transition-all duration-200 ${
                      active
                        ? 'bg-cyan-500/15 text-cyan-200 border border-cyan-500/40 shadow-sm shadow-cyan-950'
                        : 'text-slate-300 hover:text-white hover:bg-slate-800/60 border border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon
                        className={`w-5 h-5 shrink-0 transition-colors ${
                          active ? 'text-cyan-400' : 'text-slate-400'
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={`px-2 py-0.5 rounded-md text-[10px] font-mono border ${
                          item.badgeColor || 'bg-slate-800 text-slate-300 border-slate-700'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Vertical Live Integrations & Status Panel */}
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
              <div className="flex items-center gap-2">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    isHealthy ? 'bg-emerald-400 shadow-sm shadow-emerald-400/80' : 'bg-rose-500 animate-pulse'
                  }`}
                />
                <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                  Live Integrations
                </span>
              </div>
              <button
                type="button"
                onClick={onRefresh}
                disabled={loadingHealth}
                title="Refresh Integration Health"
                className="p-1 rounded-lg text-slate-400 hover:text-cyan-300 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingHealth ? 'animate-spin text-cyan-400' : ''}`} />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              {/* FastAPI */}
              <div className="flex items-center justify-between">
                <span className="text-slate-400">FastAPI Backend</span>
                <span className={`font-mono font-semibold ${isHealthy ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {isHealthy ? 'Online' : 'Offline'}
                </span>
              </div>

              {/* Qdrant */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Database className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Qdrant Cloud</span>
                </div>
                <span className="text-emerald-400 font-mono font-semibold text-[11px]">
                  {health?.integrations.qdrant_configured ? 'Connected' : 'Active'}
                </span>
              </div>

              {/* Lyzr */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Lyzr Triad</span>
                </div>
                <span className="text-emerald-400 font-mono font-semibold text-[11px]">
                  {health?.integrations.lyzr_configured ? 'Active' : 'Triad'}
                </span>
              </div>

              {/* Calendar */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Calendar className="w-3.5 h-3.5 text-amber-400" />
                  <span>Google Calendar</span>
                </div>
                <span className="text-emerald-400 font-mono font-semibold text-[11px]">Connected</span>
              </div>

              {/* Tasks */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <ListTodo className="w-3.5 h-3.5 text-blue-400" />
                  <span>Google Tasks</span>
                </div>
                <span className="text-emerald-400 font-mono font-semibold text-[11px]">Connected</span>
              </div>

              {/* Gmail */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Mail className="w-3.5 h-3.5 text-purple-400" />
                  <span>Gmail</span>
                </div>
                <span className="text-emerald-400 font-mono font-semibold text-[11px]">Drafts HITL</span>
              </div>

              {/* Telegram */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-slate-400">
                  <Send className="w-3.5 h-3.5 text-blue-400" />
                  <span>Telegram</span>
                </div>
                <span className="text-cyan-300 font-mono font-semibold text-[11px]">@Ididhswkje_bot</span>
              </div>
            </div>

            <div className="pt-1 border-t border-slate-800 text-[10px] text-slate-500 font-mono text-center">
              {health?.timestamp ? `Synced: ${new Date(health.timestamp).toLocaleTimeString()}` : 'Connected'}
            </div>
          </div>
        </div>

        {/* Bottom Tenant / User Profile Card */}
        <div className="p-4 border-t border-slate-800/80 bg-[#060a14]">
          {user ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-900 to-blue-900 border border-cyan-500/40 flex items-center justify-center text-cyan-300 font-bold text-sm shrink-0">
                    {user.email.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-white truncate" title={user.email}>
                      {user.email.split('@')[0]}
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 truncate">
                      {user.id.substring(0, 14)}...
                    </div>
                  </div>
                </div>

                {/* Logout Button */}
                <button
                  type="button"
                  onClick={onLogout}
                  title="Sign out of LifeOS"
                  className="p-2 rounded-xl text-slate-400 hover:text-rose-300 hover:bg-slate-800/80 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>

              {/* Quick Setup Button */}
              <button
                type="button"
                onClick={onOpenWizard}
                className="w-full py-2 px-3 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/40 text-cyan-200 text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
              >
                <Wand2 className="w-3.5 h-3.5 text-cyan-400" />
                <span>Integration Setup Wizard</span>
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => onOpenAuth('signup')}
                className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow"
              >
                <UserPlus className="w-4 h-4" />
                <span>Sign Up Tenant</span>
              </button>
              <button
                type="button"
                onClick={() => onOpenAuth('login')}
                className="w-full py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs flex items-center justify-center gap-2"
              >
                <LogIn className="w-4 h-4 text-cyan-400" />
                <span>Sign In</span>
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
