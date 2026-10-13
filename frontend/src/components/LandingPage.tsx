import React from 'react';
import {
  SparklesIcon,
  MicIcon,
  DatabaseIcon,
  BotIcon,
  SendIcon,
  CalendarIcon,
  ShieldCheckIcon,
  ArrowRightIcon,
  CheckCircle2Icon,
  PlayIcon,
  LayersIcon,
  ZapIcon,
  LockIcon,
} from 'lucide-react';

interface LandingPageProps {
  onOpenAuth: (mode: 'login' | 'signup') => void;
  onExploreDemo: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onOpenAuth,
  onExploreDemo,
}) => {
  return (
    <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-20 flex flex-col items-center">
      {/* Top Hackathon Banner */}
      <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-xs font-mono font-medium mb-6 shadow-lg shadow-cyan-950/50 backdrop-blur-md">
        <SparklesIcon className="w-3.5 h-3.5 text-cyan-400" />
        <span>Stop Prompting, Solo Agents Hackathon 2026 — Track 2</span>
      </div>

      {/* Hero Headline */}
      <div className="text-center max-w-4xl mx-auto space-y-5">
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white leading-[1.1]">
          The Voice-Triggered{' '}
          <span className="bg-gradient-to-r from-cyan-400 via-teal-300 to-blue-500 bg-clip-text text-transparent">
            Autonomous Personal AI Operator
          </span>
        </h1>

        <p className="text-base sm:text-lg lg:text-xl text-slate-300 max-w-2xl mx-auto font-normal leading-relaxed">
          Speak to your Omi wearable. LifeOS automatically retrieves your memory from Qdrant Cloud, orchestrates the Lyzr agent triad, executes verified actions, and coordinates Telegram approvals.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <button
            type="button"
            onClick={() => onOpenAuth('signup')}
            className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-base shadow-xl shadow-cyan-500/25 flex items-center justify-center gap-2.5 transition-all transform hover:-translate-y-0.5"
          >
            <span>Get Started Free</span>
            <ArrowRightIcon className="w-5 h-5" />
          </button>

          <button
            type="button"
            onClick={onExploreDemo}
            className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 text-slate-200 font-semibold text-base shadow flex items-center justify-center gap-2.5 transition-all backdrop-blur-md"
          >
            <PlayIcon className="w-4 h-4 text-cyan-400 fill-cyan-400" />
            <span>View Live Operator Dashboard</span>
          </button>
        </div>

        <div className="flex items-center justify-center gap-6 text-xs text-slate-400 pt-2 font-mono">
          <div className="flex items-center gap-1.5">
            <CheckCircle2Icon className="w-3.5 h-3.5 text-emerald-400" />
            <span>Zero-Click Voice Trigger</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2Icon className="w-3.5 h-3.5 text-emerald-400" />
            <span>Tenant Isolated</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2Icon className="w-3.5 h-3.5 text-emerald-400" />
            <span>Encrypted Secrets</span>
          </div>
        </div>
      </div>

      {/* Live Architecture Flow Preview */}
      <div className="w-full max-w-5xl mt-16 sm:mt-24 p-6 sm:p-8 rounded-3xl bg-[#0b1324]/90 border border-cyan-500/30 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
          <div className="flex items-center gap-2">
            <LayersIcon className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider font-mono">
              Live Collaborative Multi-Agent Pipeline
            </h3>
          </div>
          <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/80 px-2.5 py-1 rounded-full border border-cyan-500/40">
            10 Connected Nodes • SSE Stream
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-xl bg-cyan-950 flex items-center justify-center text-cyan-400 mb-2 border border-cyan-500/40">
              <MicIcon className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-white">1. Omi Voice</span>
            <span className="text-[11px] text-slate-400 mt-1">Spoken conversation webhook trigger</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-xl bg-purple-950 flex items-center justify-center text-purple-400 mb-2 border border-purple-500/40">
              <DatabaseIcon className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-white">2. Qdrant Cloud</span>
            <span className="text-[11px] text-slate-400 mt-1">384-d FastEmbed semantic recall</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-xl bg-blue-950 flex items-center justify-center text-blue-400 mb-2 border border-blue-500/40">
              <BotIcon className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-white">3. Lyzr Triad</span>
            <span className="text-[11px] text-slate-400 mt-1">Manager, Fact Finder & Data Analyst</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-xl bg-amber-950 flex items-center justify-center text-amber-400 mb-2 border border-amber-500/40">
              <CalendarIcon className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-white">4. Integrations</span>
            <span className="text-[11px] text-slate-400 mt-1">Calendar, Tasks, Gmail via Composio</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 text-center flex flex-col items-center">
            <div className="w-10 h-10 rounded-xl bg-emerald-950 flex items-center justify-center text-emerald-400 mb-2 border border-emerald-500/40">
              <SendIcon className="w-5 h-5" />
            </div>
            <span className="text-xs font-bold text-white">5. Telegram Bot</span>
            <span className="text-[11px] text-slate-400 mt-1">Interactive approvals & notifications</span>
          </div>
        </div>
      </div>

      {/* Feature Bento Grid */}
      <div className="w-full max-w-5xl mt-20">
        <div className="text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-white">
            Built for Real-World Autonomous Productivity
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            No endless prompt engineering. You speak; LifeOS does the work.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-3xl bg-[#0b1324]/80 border border-slate-800 space-y-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-950 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
              <ZapIcon className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white">Zero Dashboard Clicks</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Standard operations like calendar availability checks, task creation, and context retrieval execute autonomously the moment you finish speaking to Omi.
            </p>
          </div>

          <div className="p-6 rounded-3xl bg-[#0b1324]/80 border border-slate-800 space-y-3">
            <div className="w-10 h-10 rounded-xl bg-purple-950 border border-purple-500/40 flex items-center justify-center text-purple-400">
              <LockIcon className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white">Human-in-the-Loop Safeguards</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              High-risk actions like sending emails are staged as drafts and pushed to Telegram with inline [Approve] / [Reject] buttons. Nothing sends without your consent.
            </p>
          </div>

          <div className="p-6 rounded-3xl bg-[#0b1324]/80 border border-slate-800 space-y-3">
            <div className="w-10 h-10 rounded-xl bg-blue-950 border border-blue-500/40 flex items-center justify-center text-blue-400">
              <ShieldCheckIcon className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white">Multi-Tenant Isolation</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Every user receives an isolated tenant with dedicated Omi webhook URLs, Fernet credential encryption at rest, and payload-filtered Qdrant memory collections.
            </p>
          </div>
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="w-full max-w-4xl mt-20 p-8 sm:p-12 rounded-3xl bg-gradient-to-r from-cyan-950/60 via-blue-950/60 to-purple-950/60 border border-cyan-500/40 text-center space-y-4">
        <h3 className="text-2xl sm:text-3xl font-bold text-white">
          Experience LifeOS on Your Phone Today
        </h3>
        <p className="text-xs sm:text-sm text-slate-300 max-w-xl mx-auto">
          Create your account, hook up your Omi webhook and Telegram bot, and let your personal AI operator coordinate your schedule.
        </p>
        <div className="pt-2">
          <button
            type="button"
            onClick={() => onOpenAuth('signup')}
            className="px-8 py-3.5 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm shadow-xl shadow-cyan-500/30 transition-all"
          >
            Create Your Operator Workspace
          </button>
        </div>
      </div>
    </div>
  );
};
