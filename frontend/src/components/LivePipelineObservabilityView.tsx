import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Mic,
  Activity,
  CheckCircle2,
  Clock,
  AlertCircle,
  Brain,
  ShieldCheck,
  Send,
  Database,
  Calendar,
  ListTodo,
  Mail,
  MessageSquare,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Layers,
  Sparkles,
  Zap,
  Terminal,
} from 'lucide-react';
import {
  WorkflowRecord,
  PipelineNode,
  PipelineNodeState,
  SpecialistOutput,
  StagedAction,
  ActionExecutionResponse,
} from '../types';
import { api } from '../services/api';
import SpotlightCard from './reactbits/SpotlightCard';
import BorderGlow from './reactbits/BorderGlow';
import BlurText from './reactbits/BlurText';

interface LivePipelineObservabilityViewProps {
  uid: string;
}

export const LivePipelineObservabilityView: React.FC<LivePipelineObservabilityViewProps> = ({ uid }) => {
  const [activeWorkflow, setActiveWorkflow] = useState<WorkflowRecord | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [sseConnected, setSseConnected] = useState<boolean>(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [simText, setSimText] = useState<string>('');
  const [simulating, setSimulating] = useState<boolean>(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // 1. Fetch recent workflows
  const fetchWorkflows = useCallback(async () => {
    try {
      const list = await api.listWorkflows(uid, 30);
      setWorkflows(list);
      if (list.length > 0 && !activeWorkflow) {
        setActiveWorkflow(list[0]);
      } else if (list.length > 0 && activeWorkflow) {
        // Keep active workflow updated if its status changed
        const updated = list.find((w) => w.workflow_id === activeWorkflow.workflow_id);
        if (updated) {
          setActiveWorkflow(updated);
        }
      }
    } catch (err) {
      console.error('Failed to load workflows:', err);
    } finally {
      setLoading(false);
    }
  }, [uid, activeWorkflow]);

  // 2. Setup Server-Sent Events (SSE) for Real-Time Execution Updates
  useEffect(() => {
    fetchWorkflows();

    const sseUrl = api.getEventSourceUrl();
    const es = new EventSource(sseUrl);
    eventSourceRef.current = es;

    es.onopen = () => {
      setSseConnected(true);
    };

    es.addEventListener('ping', () => {
      setSseConnected(true);
    });

    es.addEventListener('message', (event) => {
      try {
        const payload = JSON.parse(event.data);
        // Refresh workflows on any event
        fetchWorkflows();
        if (payload.workflow_id) {
          api.getWorkflowDetails(payload.workflow_id).then((wf) => {
            setActiveWorkflow(wf);
          }).catch(console.error);
        }
      } catch (err) {
        console.error('Error parsing SSE event:', err);
      }
    });

    es.onerror = () => {
      setSseConnected(false);
    };

    // Resilient fallback polling every 2.5s for live workflow execution
    const pollInterval = setInterval(() => {
      fetchWorkflows();
    }, 2500);

    return () => {
      clearInterval(pollInterval);
      es.close();
      eventSourceRef.current = null;
    };
  }, [uid, fetchWorkflows]);

  // Handle manual voice simulation for testing
  const handleSimulateVoice = async () => {
    if (!simText.trim()) return;
    setSimulating(true);
    try {
      const data = await api.simulateVoiceInput(uid, simText);
      if (data.workflow_id) {
        const wf = await api.getWorkflowDetails(data.workflow_id);
        setActiveWorkflow(wf);
        fetchWorkflows();
      }
      setSimText('');
    } catch (err) {
      console.error('Failed to simulate voice input:', err);
    } finally {
      setSimulating(false);
    }
  };

  const PIPELINE_NODES = [
    { key: 'voice_received', label: 'Voice Received', icon: Mic },
    { key: 'transcript_stored', label: 'Transcript Stored', icon: Database },
    { key: 'memory_retrieved', label: 'Memory Retrieved', icon: Brain },
    { key: 'manager_planning', label: 'Lyzr Manager Planning', icon: Layers },
    { key: 'specialists_working', label: 'Specialist Agents Working', icon: Sparkles },
    { key: 'integrations_executing', label: 'Integrations Executing', icon: Zap },
    { key: 'telegram_approval', label: 'Telegram Approval', icon: MessageSquare },
    { key: 'verification', label: 'Verification', icon: ShieldCheck },
    { key: 'memory_updated', label: 'Qdrant Memory Updated', icon: Database },
    { key: 'completed', label: 'Completed', icon: CheckCircle2 },
  ];

  const getNodeBadge = (state: PipelineNodeState) => {
    switch (state) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
            <CheckCircle2 className="w-3 h-3" /> Completed
          </span>
        );
      case 'running':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-sky-950/90 text-sky-400 border border-sky-700 animate-pulse">
            <Activity className="w-3 h-3 animate-spin" /> In Progress
          </span>
        );
      case 'awaiting_telegram_approval':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-950/90 text-amber-300 border border-amber-600 animate-pulse">
            <Clock className="w-3 h-3" /> Awaiting Telegram Approval
          </span>
        );
      case 'skipped':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-900 text-slate-400 border border-slate-800">
            Skipped
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-950/90 text-rose-400 border border-rose-800">
            <AlertCircle className="w-3 h-3" /> Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-900/60 text-slate-500 border border-slate-800/50">
            Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Real-time Voice Architecture Status */}
      <BorderGlow
        animated={true}
        backgroundColor="rgba(8, 14, 28, 0.65)"
        colors={['#0ea5e9', '#6366f1', '#10b981']}
        glowColor="198 93 60"
        glowIntensity={1.3}
        glowRadius={28}
        borderRadius={16}
        className="w-full shadow-2xl backdrop-blur-xl"
      >
        <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-600/20 border border-sky-500/30 flex items-center justify-center text-sky-400 shadow-inner">
              <Mic className="w-5 h-5 animate-pulse text-sky-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <BlurText
                  text="Voice-Triggered Autonomous Operator"
                  delay={30}
                  animateBy="words"
                  direction="top"
                  className="text-base font-bold text-white tracking-tight"
                />
                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                  sseConnected
                    ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-700/60'
                    : 'bg-amber-950/80 text-amber-300 border border-amber-700/60'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${sseConnected ? 'bg-emerald-400 animate-ping' : 'bg-amber-400'}`} />
                  {sseConnected ? 'SSE Live Stream Active' : 'Connecting Stream...'}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Spoken input from Omi starts execution automatically. Low-risk operations run autonomously; Telegram handles approvals.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchWorkflows}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700/60 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>
        </div>
      </BorderGlow>

      {/* SECTION A: VOICE INPUT INSPECTOR */}
      <BorderGlow
        animated={true}
        backgroundColor="rgba(8, 14, 28, 0.65)"
        colors={['#8b5cf6', '#38bdf8', '#c084fc']}
        glowColor="270 80 75"
        glowIntensity={1.3}
        glowRadius={26}
        borderRadius={16}
        className="w-full shadow-2xl backdrop-blur-xl"
      >
        <div className="p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Mic className="w-4 h-4 text-sky-400" />
              <BlurText
                text="Voice Input Trigger"
                delay={40}
                animateBy="words"
                direction="top"
                className="text-xs font-bold text-slate-200 uppercase tracking-wider"
              />
            </div>
            <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
              {activeWorkflow && (
                <>
                  <span>Conv: <strong className="text-sky-300">{activeWorkflow.conversation_id}</strong></span>
                  <span>•</span>
                  <span>Workflow: <strong className="text-slate-200">{activeWorkflow.workflow_id}</strong></span>
                  <span>•</span>
                  <span>{new Date(activeWorkflow.created_at).toLocaleTimeString()}</span>
                </>
              )}
            </div>
          </div>

          {activeWorkflow ? (
            <SpotlightCard
              ambient={true}
              spotlightColor="rgba(56, 189, 248, 0.35)"
              intensity={0.35}
              borderGlow={0.7}
              spotlightSize={260}
              style={{
                '--spotlight-card-surface': 'rgba(6, 11, 23, 0.75)',
                '--spotlight-card-border': 'rgba(56, 189, 248, 0.25)',
                '--spotlight-card-padding': '1rem',
                '--spotlight-card-radius': '0.75rem',
              }}
              className="shadow-inner"
            >
              <div className="flex items-start gap-3">
                <div className="mt-1 w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-pulse" />
                <div className="flex-1">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Spoken Transcript Evidence:</span>
                  <p className="text-sm font-medium text-slate-100 mt-1 leading-relaxed">
                    "{activeWorkflow.transcript}"
                  </p>
                </div>
              </div>
            </SpotlightCard>
          ) : (
            <div className="text-center py-6 text-slate-400 text-xs">
              No voice conversation received yet. Speak into your Omi mobile app to start execution automatically.
            </div>
          )}
        </div>
      </BorderGlow>

      {/* SECTION B: LIVE 10-NODE EXECUTION PIPELINE */}
      <div className="bg-[#080d1b]/55 border border-sky-500/20 rounded-2xl p-5 shadow-2xl backdrop-blur-xl ring-1 ring-white/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-sky-400" />
            <BlurText
              text="Live Execution Pipeline (10 Connected Nodes)"
              delay={35}
              animateBy="words"
              direction="top"
              className="text-xs font-bold text-slate-200 uppercase tracking-wider"
            />
          </div>
          {activeWorkflow && (
            <span className="text-xs font-mono text-slate-400">
              Stage: <strong className="text-sky-400">{activeWorkflow.current_stage}</strong>
            </span>
          )}
        </div>

        {/* Nodes Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
          {PIPELINE_NODES.map((nodeMeta, idx) => {
            const nodeData = activeWorkflow?.nodes?.[nodeMeta.key] || {
              id: nodeMeta.key,
              label: nodeMeta.label,
              state: 'pending' as PipelineNodeState,
            };
            const Icon = nodeMeta.icon;
            const isSelected = selectedNodeId === nodeMeta.key;
            const isRunning = nodeData.state === 'running';
            // Default highlight: currently running node, or selected node, or completed terminal stage
            const shouldGlow = isRunning || (selectedNodeId ? isSelected : (activeWorkflow?.status === 'COMPLETED' ? idx === 9 : (activeWorkflow?.current_stage ? nodeMeta.key.toLowerCase().includes(activeWorkflow.current_stage.toLowerCase()) : idx === 0)));

            if (shouldGlow) {
              return (
                <BorderGlow
                  key={nodeMeta.key}
                  animated={true}
                  className="cursor-pointer transition-all shadow-xl"
                  backgroundColor="rgba(8, 14, 28, 0.8)"
                  colors={['#0ea5e9', '#38bdf8', '#818cf8', '#a855f7']}
                  glowColor="198 93 60"
                  glowIntensity={1.4}
                  glowRadius={28}
                  borderRadius={12}
                  edgeSensitivity={15}
                  onClick={() => setSelectedNodeId(nodeMeta.key)}
                >
                  <div className="p-3.5 flex flex-col justify-between min-h-[110px] w-full">
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-mono text-slate-300 font-bold">{idx + 1}</span>
                        {getNodeBadge(nodeData.state)}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <Icon className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                        <h3 className="text-xs font-bold text-slate-100 tracking-tight leading-snug">{nodeMeta.label}</h3>
                      </div>
                    </div>

                    <div className="mt-2 pt-2 border-t border-slate-700/60 text-[11px] text-slate-200 line-clamp-2">
                      {nodeData.summary || 'Executing active stage...'}
                    </div>
                  </div>
                </BorderGlow>
              );
            }

            return (
              <SpotlightCard
                key={nodeMeta.key}
                onClick={() => setSelectedNodeId(nodeMeta.key)}
                ambient={true}
                spotlightColor="rgba(56, 189, 248, 0.45)"
                intensity={0.45}
                borderGlow={0.8}
                spotlightSize={220}
                style={{
                  '--spotlight-card-surface': 'rgba(8, 14, 28, 0.65)',
                  '--spotlight-card-border': 'rgba(56, 189, 248, 0.22)',
                  '--spotlight-card-padding': '0.875rem',
                  '--spotlight-card-radius': '0.75rem',
                }}
                className="cursor-pointer transition-all flex flex-col justify-between min-h-[110px] hover:border-sky-400/50 shadow-md backdrop-blur-md"
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-mono text-slate-500 font-semibold">{idx + 1}</span>
                    {getNodeBadge(nodeData.state)}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <Icon className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                    <h3 className="text-xs font-semibold text-slate-200 tracking-tight leading-snug">{nodeMeta.label}</h3>
                  </div>
                </div>

                <div className="mt-2 pt-2 border-t border-slate-800/40 text-[11px] text-slate-400 line-clamp-2">
                  {nodeData.summary || 'Awaiting execution...'}
                </div>
              </SpotlightCard>
            );
          })}
        </div>

        {/* Selected Node Details Drawer */}
        {selectedNodeId && activeWorkflow?.nodes?.[selectedNodeId] && (
          <div className="mt-4 p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-300">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
              <span className="font-semibold text-sky-400 uppercase tracking-wider">
                Node Details: {activeWorkflow.nodes[selectedNodeId].label}
              </span>
              <button
                onClick={() => setSelectedNodeId(null)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="space-y-1.5 font-mono text-[11px]">
              <div>Status: <strong className="text-slate-200">{activeWorkflow.nodes[selectedNodeId].state}</strong></div>
              {activeWorkflow.nodes[selectedNodeId].duration_ms && (
                <div>Duration: <strong className="text-emerald-400">{activeWorkflow.nodes[selectedNodeId].duration_ms} ms</strong></div>
              )}
              {activeWorkflow.nodes[selectedNodeId].summary && (
                <div>Summary: <span className="text-slate-300">{activeWorkflow.nodes[selectedNodeId].summary}</span></div>
              )}
              {activeWorkflow.nodes[selectedNodeId].details && (
                <pre className="bg-[#050811] p-2 rounded border border-slate-800/80 text-slate-400 overflow-x-auto text-[10px] mt-2">
                  {JSON.stringify(activeWorkflow.nodes[selectedNodeId].details, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </div>

      {/* SECTION C & D: AGENT ACTIVITY & ACTION RESULTS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SECTION C: MULTI-AGENT ACTIVITY */}
        <div className="bg-[#080d1b]/55 border border-purple-500/20 rounded-2xl p-5 shadow-2xl backdrop-blur-xl ring-1 ring-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Layers className="w-4 h-4 text-sky-400" />
              <BlurText
                text="Multi-Agent Activity (Lyzr Triad)"
                delay={35}
                animateBy="words"
                direction="top"
                className="text-xs font-bold text-slate-200 uppercase tracking-wider"
              />
            </div>

            {/* Manager Plan Summary */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-1.5">
                <Brain className="w-3.5 h-3.5 text-purple-400" />
                <span className="text-xs font-semibold text-slate-200">Lyzr Manager Plan</span>
              </div>
              <SpotlightCard
                ambient={true}
                spotlightColor="rgba(168, 85, 247, 0.4)"
                intensity={0.4}
                borderGlow={0.8}
                spotlightSize={240}
                style={{
                  '--spotlight-card-surface': 'rgba(8, 14, 28, 0.65)',
                  '--spotlight-card-border': 'rgba(168, 85, 247, 0.35)',
                  '--spotlight-card-padding': '1rem',
                  '--spotlight-card-radius': '0.75rem',
                }}
                className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed shadow-lg backdrop-blur-md"
              >
                {activeWorkflow?.plan_summary || 'Manager synthesizes plan upon voice intake...'}
              </SpotlightCard>
            </div>

            {/* Specialists Output Cards */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-1">
                <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                <span className="text-xs font-semibold text-slate-200">Specialist Contributions</span>
              </div>

              {activeWorkflow?.specialist_outputs && activeWorkflow.specialist_outputs.length > 0 ? (
                activeWorkflow.specialist_outputs.map((sp, idx) => (
                  <SpotlightCard
                    key={idx}
                    ambient={true}
                    spotlightColor="rgba(56, 189, 248, 0.35)"
                    intensity={0.35}
                    borderGlow={0.7}
                    spotlightSize={200}
                    style={{
                      '--spotlight-card-surface': 'rgba(8, 14, 28, 0.65)',
                      '--spotlight-card-border': 'rgba(56, 189, 248, 0.25)',
                      '--spotlight-card-padding': '0.875rem',
                      '--spotlight-card-radius': '0.75rem',
                    }}
                    className="text-xs shadow-md backdrop-blur-md"
                  >
                    <div className="flex items-center justify-between text-[11px] font-semibold text-sky-300 mb-1">
                      <span>{sp.agent_name}</span>
                      <span className="text-slate-400 font-mono text-[10px]">{sp.role}</span>
                    </div>
                    <p className="text-slate-200 text-[11px] whitespace-pre-wrap">{sp.output}</p>
                  </SpotlightCard>
                ))
              ) : (
                <div className="text-slate-400 text-xs italic p-3 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  Specialists invoke when operations and evidence require verification.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* SECTION D: ACTION RESULTS */}
        <div className="bg-[#080d1b]/55 border border-emerald-500/20 rounded-2xl p-5 shadow-2xl backdrop-blur-xl ring-1 ring-white/10 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-emerald-400" />
                <BlurText
                  text="Executed & Verified Actions"
                  delay={35}
                  animateBy="words"
                  direction="top"
                  className="text-xs font-bold text-slate-200 uppercase tracking-wider"
                />
              </div>
              <span className="text-[11px] font-mono text-slate-400">
                {activeWorkflow?.action_results?.length || 0} Executed
              </span>
            </div>

            <div className="space-y-3">
              {activeWorkflow?.actions && activeWorkflow.actions.length > 0 ? (
                activeWorkflow.actions.map((act) => {
                  const execRes = activeWorkflow.action_results?.find((r) => r.action_id === act.action_id);
                  const isTask = act.action_type === 'create_task';
                  const isDraft = act.action_type === 'create_gmail_draft';
                  const isCalendar = act.action_type === 'create_calendar_event';
                  const isReadCalendar = act.action_type === 'read_calendar';
                  const isStaged = act.status === 'staged';

                  const actionContent = (
                    <>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {isTask && <ListTodo className="w-4 h-4 text-emerald-400" />}
                          {isDraft && <Mail className="w-4 h-4 text-sky-400" />}
                          {isCalendar && <Calendar className="w-4 h-4 text-amber-400" />}
                          {isReadCalendar && <Calendar className="w-4 h-4 text-sky-400" />}
                          <span className="text-xs font-bold text-slate-100">{act.title}</span>
                        </div>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                          execRes?.verified || act.status === 'completed'
                            ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                            : act.status === 'staged'
                            ? 'bg-amber-950/80 text-amber-300 border border-amber-800 animate-pulse'
                            : 'bg-slate-800 text-slate-400'
                        }`}>
                          {execRes?.verified ? 'Verified Live' : act.status.toUpperCase()}
                        </span>
                      </div>

                      <p className="text-xs text-slate-300 line-clamp-2">{act.description}</p>

                      <div className="pt-2 border-t border-slate-700/60 flex items-center justify-between text-[10px] font-mono text-slate-400">
                        <span>Action: {act.action_id}</span>
                        {isDraft && act.status === 'staged' && (
                          <span className="text-amber-400 font-sans font-semibold">
                            📱 Telegram Approval Sent
                          </span>
                        )}
                        {execRes?.memory_id && (
                          <span className="text-emerald-400 font-sans font-semibold">
                            ✓ Memory Stored ({execRes.memory_id.slice(0, 8)}...)
                          </span>
                        )}
                      </div>
                    </>
                  );

                  if (isStaged) {
                    return (
                      <BorderGlow
                        key={act.action_id}
                        animated={true}
                        backgroundColor="rgba(8, 14, 28, 0.85)"
                        colors={['#f59e0b', '#fbbf24', '#0ea5e9']}
                        glowColor="45 90 60"
                        glowIntensity={1.35}
                        glowRadius={24}
                        borderRadius={12}
                        className="w-full shadow-lg"
                      >
                        <div className="p-3.5 flex flex-col gap-2 w-full">
                          {actionContent}
                        </div>
                      </BorderGlow>
                    );
                  }

                  return (
                    <SpotlightCard
                      key={act.action_id}
                      ambient={true}
                      spotlightColor="rgba(16, 185, 129, 0.35)"
                      intensity={0.35}
                      borderGlow={0.75}
                      spotlightSize={220}
                      style={{
                        '--spotlight-card-surface': 'rgba(8, 14, 28, 0.65)',
                        '--spotlight-card-border': 'rgba(16, 185, 129, 0.25)',
                        '--spotlight-card-padding': '0.875rem',
                        '--spotlight-card-radius': '0.75rem',
                      }}
                      className="flex flex-col gap-2 shadow-md backdrop-blur-md"
                    >
                      {actionContent}
                    </SpotlightCard>
                  );
                })
              ) : (
                <div className="text-slate-400 text-xs italic p-4 text-center rounded-xl bg-slate-900/40 border border-slate-800/60">
                  No actions created yet for this workflow.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* SECTION: GOOGLE CALENDAR INSPECTION & TELEGRAM DISPATCH */}
      {(activeWorkflow?.calendar_result || activeWorkflow?.telegram_delivery) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* CALENDAR INSPECTION CARD */}
          <div className="bg-[#080d1b]/55 border border-amber-500/20 rounded-2xl p-5 shadow-2xl backdrop-blur-xl ring-1 ring-white/10 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-amber-400" />
                  <BlurText
                    text="Google Calendar Inspection & Free Time"
                    delay={35}
                    animateBy="words"
                    direction="top"
                    className="text-xs font-bold text-slate-200 uppercase tracking-wider"
                  />
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                  Verified Live Integration
                </span>
              </div>

              {activeWorkflow?.calendar_result ? (
                <div className="space-y-3.5">
                  <SpotlightCard
                    ambient={true}
                    spotlightColor="rgba(245, 158, 11, 0.35)"
                    intensity={0.35}
                    borderGlow={0.75}
                    spotlightSize={220}
                    style={{
                      '--spotlight-card-surface': 'rgba(8, 14, 28, 0.65)',
                      '--spotlight-card-border': 'rgba(245, 158, 11, 0.25)',
                      '--spotlight-card-padding': '0.875rem',
                      '--spotlight-card-radius': '0.75rem',
                    }}
                    className="grid grid-cols-3 gap-2 text-xs shadow-md backdrop-blur-md"
                  >
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Target Date</span>
                      <span className="font-semibold text-slate-100">{activeWorkflow.calendar_result.requested_date}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Timezone</span>
                      <span className="font-mono text-slate-100">{activeWorkflow.calendar_result.timezone}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Free Time</span>
                      <span className="font-bold text-emerald-400">{activeWorkflow.calendar_result.total_free_formatted}</span>
                    </div>
                  </SpotlightCard>

                  {/* Meetings List */}
                  <div>
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-200 mb-1.5">
                      <span>Scheduled Meetings</span>
                      <span className="text-[11px] font-mono text-slate-400">
                        {activeWorkflow.calendar_result.meetings_count} meeting(s)
                      </span>
                    </div>
                    {activeWorkflow.calendar_result.meetings && activeWorkflow.calendar_result.meetings.length > 0 ? (
                      <div className="space-y-1.5 max-h-36 overflow-y-auto">
                        {activeWorkflow.calendar_result.meetings.map((m: any, idx: number) => (
                          <div key={idx} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-700/60 flex items-center justify-between text-xs">
                            <span className="font-medium text-slate-200 truncate">{m.summary}</span>
                            <span className="text-[10px] font-mono text-slate-400 shrink-0 ml-2">
                              {m.start_time?.slice(11, 16)} - {m.end_time?.slice(11, 16)}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 italic p-2.5 rounded-lg bg-slate-900/40 border border-slate-800/60">
                        No meetings scheduled for this day (100% free working hours).
                      </p>
                    )}
                  </div>

                  {/* Free Time Intervals */}
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block mb-1.5">Available Free Intervals (09:00 - 18:00)</span>
                    <div className="space-y-1.5">
                      {activeWorkflow.calendar_result.free_intervals && activeWorkflow.calendar_result.free_intervals.length > 0 ? (
                        activeWorkflow.calendar_result.free_intervals.map((slot: any, idx: number) => (
                          <div key={idx} className="p-2 rounded-lg bg-emerald-950/30 border border-emerald-900/50 flex items-center justify-between text-xs">
                            <span className="font-mono text-emerald-300">{slot.start} - {slot.end}</span>
                            <span className="font-semibold text-emerald-400 text-[11px]">{slot.duration_formatted}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-400 italic">No free intervals available.</p>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-4 text-center text-xs text-slate-400 italic rounded-xl bg-slate-900/40 border border-slate-800/60">
                  Calendar inspection awaiting execution or not requested.
                </div>
              )}
            </div>
          </div>

          {/* TELEGRAM NOTIFICATION DELIVERY CARD */}
          <div className="bg-[#080d1b]/55 border border-sky-500/20 rounded-2xl p-5 shadow-2xl backdrop-blur-xl ring-1 ring-white/10 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-sky-400" />
                  <BlurText
                    text="Telegram Notification & Delivery"
                    delay={35}
                    animateBy="words"
                    direction="top"
                    className="text-xs font-bold text-slate-200 uppercase tracking-wider"
                  />
                </div>
                {activeWorkflow?.telegram_delivery && (
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    activeWorkflow.telegram_delivery.status === 'delivered'
                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                      : activeWorkflow.telegram_delivery.status === 'NEEDS_CONFIGURATION'
                      ? 'bg-amber-950/80 text-amber-300 border border-amber-800'
                      : 'bg-rose-950/80 text-rose-400 border border-rose-800'
                  }`}>
                    {activeWorkflow.telegram_delivery.status === 'delivered'
                      ? `DELIVERED (ID #${activeWorkflow.telegram_delivery.message_id || 'OK'})`
                      : activeWorkflow.telegram_delivery.status.toUpperCase()}
                  </span>
                )}
              </div>

              {activeWorkflow?.telegram_delivery ? (
                <div className="space-y-3">
                  {/* Status banner */}
                  {activeWorkflow.telegram_delivery.status === 'NEEDS_CONFIGURATION' && (
                    <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-800/70 text-xs text-amber-300 flex items-start gap-2.5">
                      <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold block">Configuration Required:</span>
                        <p className="mt-0.5 text-amber-200/90 leading-relaxed">
                          Telegram chat ID is not registered. Send <strong className="font-mono text-white">/start</strong> to{' '}
                          <a
                            href="https://t.me/Ididhswkje_bot"
                            target="_blank"
                            rel="noreferrer"
                            className="underline text-sky-300 font-semibold"
                          >
                            @Ididhswkje_bot
                          </a>{' '}
                          to connect your chat for automatic report deliveries.
                        </p>
                      </div>
                    </div>
                  )}

                  {activeWorkflow.telegram_delivery.status === 'delivered' && (
                    <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-800/70 text-xs text-emerald-300 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span>Dispatched to Telegram chat: <strong className="font-mono">{activeWorkflow.telegram_delivery.chat_id}</strong></span>
                      </div>
                      {activeWorkflow.telegram_delivery.message_id && (
                        <span className="font-mono text-[10px] text-emerald-400/80">
                          Msg #{activeWorkflow.telegram_delivery.message_id}
                        </span>
                      )}
                    </div>
                  )}

                  {activeWorkflow.telegram_delivery.status === 'failed' && (
                    <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/70 text-xs text-rose-300 flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold block">Delivery Failed:</span>
                        <p className="mt-0.5 text-rose-200/90">{activeWorkflow.telegram_delivery.error_message || 'Could not deliver to Telegram.'}</p>
                      </div>
                    </div>
                  )}

                  {/* Message Preview */}
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5">
                      Delivered Message Preview
                    </span>
                    <SpotlightCard
                      ambient={true}
                      spotlightColor="rgba(56, 189, 248, 0.35)"
                      intensity={0.35}
                      borderGlow={0.75}
                      spotlightSize={220}
                      style={{
                        '--spotlight-card-surface': 'rgba(8, 14, 28, 0.65)',
                        '--spotlight-card-border': 'rgba(56, 189, 248, 0.25)',
                        '--spotlight-card-padding': '1rem',
                        '--spotlight-card-radius': '0.75rem',
                      }}
                      className="text-xs text-slate-200 font-mono whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed shadow-md backdrop-blur-md"
                    >
                      {activeWorkflow.telegram_delivery.text || activeWorkflow.calendar_result?.report_markdown || 'No message content available.'}
                    </SpotlightCard>
                  </div>
                </div>
              ) : (
                <div className="p-4 text-center text-xs text-slate-400 italic rounded-xl bg-slate-900/40 border border-slate-800/60">
                  No Telegram notification dispatched yet for this workflow.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SECTION E: MEMORY LOOP */}
      <div className="bg-[#080d1b]/55 border border-cyan-500/20 rounded-2xl p-5 shadow-2xl backdrop-blur-xl ring-1 ring-white/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-sky-400" />
            <BlurText
              text="Closed-Loop Memory (Qdrant Cloud)"
              delay={35}
              animateBy="words"
              direction="top"
              className="text-xs font-bold text-slate-200 uppercase tracking-wider"
            />
          </div>
          <span className="text-xs text-slate-400 font-mono">
            Retrieved: {activeWorkflow?.retrieved_memories?.length || 0} • Committed: {activeWorkflow?.saved_memories?.length || 0}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Retrieved Context */}
          <SpotlightCard
            ambient={true}
            spotlightColor="rgba(56, 189, 248, 0.3)"
            intensity={0.3}
            borderGlow={0.65}
            spotlightSize={200}
            style={{
              '--spotlight-card-surface': 'rgba(8, 14, 28, 0.65)',
              '--spotlight-card-border': 'rgba(56, 189, 248, 0.2)',
              '--spotlight-card-padding': '0.875rem',
              '--spotlight-card-radius': '0.75rem',
            }}
            className="shadow-inner backdrop-blur-md"
          >
            <span className="text-[11px] font-semibold text-sky-400 uppercase tracking-wider block mb-2">
              Context Ingested from Qdrant:
            </span>
            {activeWorkflow?.retrieved_memories && activeWorkflow.retrieved_memories.length > 0 ? (
              <div className="space-y-2">
                {activeWorkflow.retrieved_memories.map((m: any, idx: number) => (
                  <div key={idx} className="p-2 rounded bg-slate-900/60 border border-slate-700/60 text-[11px] text-slate-300">
                    <p className="line-clamp-2">{m.content}</p>
                    <span className="text-[9px] font-mono text-slate-400 mt-1 block">ID: {m.id}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No prior relevant memories found for this topic.</p>
            )}
          </SpotlightCard>

          {/* Committed Memory */}
          <SpotlightCard
            ambient={true}
            spotlightColor="rgba(16, 185, 129, 0.3)"
            intensity={0.3}
            borderGlow={0.65}
            spotlightSize={200}
            style={{
              '--spotlight-card-surface': 'rgba(8, 14, 28, 0.65)',
              '--spotlight-card-border': 'rgba(16, 185, 129, 0.2)',
              '--spotlight-card-padding': '0.875rem',
              '--spotlight-card-radius': '0.75rem',
            }}
            className="shadow-inner backdrop-blur-md"
          >
            <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider block mb-2">
              Verified Outcomes Committed to Memory:
            </span>
            {activeWorkflow?.saved_memories && activeWorkflow.saved_memories.length > 0 ? (
              <div className="space-y-2">
                {activeWorkflow.saved_memories.map((m: any, idx: number) => (
                  <div key={idx} className="p-2 rounded bg-slate-900/60 border border-emerald-900/50 text-[11px] text-slate-300">
                    <p className="line-clamp-2">{m.content}</p>
                    <span className="text-[9px] font-mono text-emerald-400/80 mt-1 block">Committed ID: {m.id}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">Outcomes are committed upon verified completion.</p>
            )}
          </SpotlightCard>
        </div>
      </div>

      {/* SECTION F: WORKFLOW HISTORY */}
      <div className="bg-[#080d1b]/55 border border-slate-700/50 rounded-2xl p-5 shadow-2xl backdrop-blur-xl ring-1 ring-white/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-400" />
            <BlurText
              text="Voice Workflow History"
              delay={35}
              animateBy="words"
              direction="top"
              className="text-xs font-bold text-slate-200 uppercase tracking-wider"
            />
          </div>
          <span className="text-xs text-slate-400 font-mono">{workflows.length} Workflows</span>
        </div>

        {workflows.length > 0 ? (
          <div className="divide-y divide-slate-800/60">
            {workflows.map((wf) => {
              const isSelected = activeWorkflow?.workflow_id === wf.workflow_id;
              return (
                <div
                  key={wf.workflow_id}
                  onClick={() => setActiveWorkflow(wf)}
                  className={`p-3 rounded-xl transition-all cursor-pointer flex items-center justify-between gap-4 ${
                    isSelected ? 'bg-sky-950/40 border border-sky-600/40' : 'hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                      wf.status === 'COMPLETED' ? 'bg-emerald-400' : wf.status === 'AWAITING_APPROVAL' ? 'bg-amber-400 animate-pulse' : 'bg-sky-400'
                    }`} />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-200 truncate">{wf.workflow_id}</span>
                        <span className="text-[10px] font-mono text-slate-500">{new Date(wf.created_at).toLocaleTimeString()}</span>
                      </div>
                      <p className="text-xs text-slate-400 truncate mt-0.5">{wf.transcript}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                      wf.status === 'COMPLETED'
                        ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/60'
                        : wf.status === 'AWAITING_APPROVAL'
                        ? 'bg-amber-950/80 text-amber-300 border border-amber-800/60'
                        : 'bg-sky-950/80 text-sky-300 border border-sky-800/60'
                    }`}>
                      {wf.status}
                    </span>
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-6 text-slate-500 text-xs">
            No workflows recorded yet.
          </div>
        )}
      </div>

      {/* DEV / TEST SIMULATOR (COLLAPSIBLE, SEPARATE FROM MAIN WORKFLOW) */}
      <details className="bg-slate-900/40 border border-slate-800/60 rounded-2xl p-4 text-xs text-slate-400">
        <summary className="cursor-pointer font-semibold text-slate-300 flex items-center gap-2 select-none">
          <Terminal className="w-4 h-4 text-slate-400" />
          Development Voice Simulator (For testing without phone)
        </summary>
        <div className="mt-3 pt-3 border-t border-slate-800/60 space-y-2">
          <p className="text-[11px] text-slate-400">
            Submit a test transcript simulating an Omi completed conversation:
          </p>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={simText}
              onChange={(e) => setSimText(e.target.value)}
              placeholder="e.g. LifeOS, prepare the Stop Prompting Hackathon submission and email the team."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500"
            />
            <button
              onClick={handleSimulateVoice}
              disabled={simulating || !simText.trim()}
              className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white transition-colors shrink-0"
            >
              {simulating ? 'Processing...' : 'Simulate Voice'}
            </button>
          </div>
        </div>
      </details>
    </div>
  );
};
