export interface ServiceIntegrations {
  lyzr_configured: boolean;
  qdrant_configured: boolean;
  omi_configured: boolean;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
  integrations: ServiceIntegrations;
}

export interface MemoryMetadata {
  source?: 'omi_conversation_summary' | 'omi_conversation_segment' | 'omi_realtime_segment' | 'manual' | string;
  conversation_id?: string;
  session_id?: string;
  speaker?: string;
  is_user?: boolean;
  start?: number;
  end?: number;
  title?: string;
  category?: string;
  started_at?: string;
  finished_at?: string;
  [key: string]: any;
}

export interface MemoryItem {
  id: string;
  uid: string;
  content: string;
  display_text?: string;
  metadata: MemoryMetadata;
  score?: number | null;
  created_at?: string;
}

export interface MemorySearchRequest {
  uid: string;
  query: string;
  limit?: number;
  score_threshold?: number;
}

export interface MemorySearchResponse {
  memories: MemoryItem[];
  total_found: number;
  query: string;
  uid: string;
}

export interface MemoryCreateRequest {
  uid: string;
  content: string;
  metadata?: Record<string, any>;
}

export interface ExecutionEvent {
  step: 'request_validation' | 'memory_retrieval' | 'prompt_synthesis' | 'agent_reasoning' | 'final_response' | string;
  timestamp: string;
  status: 'pending' | 'started' | 'completed' | 'failed' | string;
  details?: Record<string, any>;
}

export interface AskRequest {
  uid: string;
  question: string;
  session_id?: string;
}

export interface AskResponse {
  answer: string;
  supporting_memories: MemoryItem[];
  execution_events: ExecutionEvent[];
  agent_id?: string;
  session_id?: string;
  specialist_outputs?: Record<string, string>;
}

export type ActionType =
  | 'create_task'
  | 'create_calendar_event'
  | 'create_gmail_draft'
  | 'read_calendar'
  | 'list_tasks';
export type ActionStatus = 'staged' | 'approved' | 'rejected' | 'completed' | 'failed' | 'expired';

export interface StagedAction {
  action_id: string;
  uid: string;
  action_type: ActionType;
  title: string;
  description: string;
  parameters: Record<string, any>;
  status: ActionStatus;
  created_at: string;
  expires_at: string;
  idempotency_key: string;
  execution_result?: Record<string, any> | null;
  verification_status?: string | null;
  error_message?: string | null;
}

export interface CalendarEventItem {
  id?: string;
  summary: string;
  start_time: string;
  end_time: string;
  description?: string;
}

export interface TaskItem {
  id?: string;
  title: string;
  status?: string;
  due?: string;
  notes?: string;
}

export interface TimeSlot {
  start_time: string;
  end_time: string;
  duration_minutes: number;
  label?: string;
}

export interface PlanRequest {
  uid: string;
  prompt: string;
  target_date?: string;
  timezone?: string;
}

export interface PlanResponse {
  uid: string;
  plan_summary: string;
  target_date: string;
  existing_events: CalendarEventItem[];
  pending_tasks: TaskItem[];
  suggested_slots: TimeSlot[];
  staged_actions: StagedAction[];
  execution_events: ExecutionEvent[];
}

export interface ActionExecutionResponse {
  action_id: string;
  status: ActionStatus;
  message: string;
  execution_result?: Record<string, any>;
  verified: boolean;
  memory_id?: string;
  notification?: Record<string, any> | null;
}

export interface TelegramNotificationRecord {
  notification_id: string;
  event_type: string;
  action_id?: string | null;
  chat_id?: string | null;
  text: string;
  status: 'delivered' | 'failed' | 'skipped_no_chat_id' | 'NEEDS_CONFIGURATION' | string;
  timestamp: string;
  message_id?: number | null;
  error_message?: string | null;
}

export interface DraftRequest {
  uid: string;
  prompt: string;
  recipient_email?: string;
  subject?: string;
}

export interface DraftResponse {
  uid: string;
  staged_action: StagedAction;
  context_used: string[];
  execution_events: ExecutionEvent[];
}

export interface IntegrationStatusDetail {
  status: 'connected' | 'unconfigured' | 'error' | string;
  provider?: string;
  role: string;
  collection?: string;
  manager_id?: string;
  bot_username?: string;
  chat_id_configured?: boolean;
}

export interface LifeOSStatusResponse {
  status: string;
  app_name: string;
  version: string;
  timestamp: string;
  integrations: Record<string, IntegrationStatusDetail>;
}

export type PipelineNodeState =
  | 'pending'
  | 'running'
  | 'completed'
  | 'awaiting_telegram_approval'
  | 'failed'
  | 'skipped';

export interface PipelineNode {
  id: string;
  label: string;
  state: PipelineNodeState;
  start_time?: string | null;
  end_time?: string | null;
  duration_ms?: number | null;
  summary?: string | null;
  error?: string | null;
  details?: Record<string, any>;
}

export interface SpecialistOutput {
  agent_id: string;
  agent_name: string;
  role: string;
  output: string;
  timestamp: string;
}

export interface WorkflowRecord {
  workflow_id: string;
  user_id: string;
  conversation_id: string;
  transcript: string;
  created_at: string;
  updated_at: string;
  status:
    | 'RECEIVED'
    | 'RUNNING'
    | 'AWAITING_APPROVAL'
    | 'COMPLETED'
    | 'PARTIALLY_COMPLETED'
    | 'FAILED'
    | 'DELIVERY_FAILED'
    | 'NEEDS_CONFIGURATION'
    | 'REJECTED';
  current_stage: string;
  nodes: Record<string, PipelineNode>;
  plan_summary?: string | null;
  specialist_outputs: SpecialistOutput[];
  action_ids: string[];
  actions: StagedAction[];
  action_results: ActionExecutionResponse[];
  calendar_result?: Record<string, any> | null;
  telegram_delivery?: Record<string, any> | null;
  retrieved_memories: any[];
  saved_memories: any[];
  execution_events: ExecutionEvent[];
  error_details?: string | null;
  idempotency_hash: string;
}

export interface WorkflowEventPayload {
  event_type: string;
  workflow_id: string;
  user_id: string;
  stage: string;
  status: string;
  timestamp: string;
  data: Record<string, any>;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  omi_webhook_token: string;
  telegram_chat_id?: string | null;
  telegram_pair_code?: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface IntegrationStatusItem {
  integration_type: string;
  status: 'connected' | 'unconfigured' | 'error';
  last_verified_at?: string | null;
  masked_fields: Record<string, string>;
  provider_name?: string | null;
  details?: Record<string, any> | null;
}

export interface UserIntegrationsResponse {
  integrations: Record<string, IntegrationStatusItem>;
}

export interface OmiWebhookInfo {
  webhook_token: string;
  conversation_webhook_url: string;
  realtime_webhook_url: string;
  setup_steps: string[];
}



