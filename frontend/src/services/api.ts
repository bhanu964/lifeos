import { apiConfig } from '../config/apiConfig';
import {
  HealthResponse,
  MemoryItem,
  MemorySearchRequest,
  MemorySearchResponse,
  MemoryCreateRequest,
  AskRequest,
  AskResponse,
  PlanRequest,
  PlanResponse,
  StagedAction,
  ActionExecutionResponse,
  LifeOSStatusResponse,
  WorkflowRecord,
  User,
  TokenResponse,
  IntegrationStatusItem,
  UserIntegrationsResponse,
  OmiWebhookInfo,
} from '../types';

const TOKEN_KEY = 'lifeos_access_token';

let memoryToken: string | null = null;

try {
  memoryToken = localStorage.getItem(TOKEN_KEY);
} catch {
  // SSR or restricted environment safe
}

function getAuthHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extraHeaders };
  const token = memoryToken || (typeof localStorage !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null);
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse<T>(res: Response, endpoint: string): Promise<T> {
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore JSON parse error
    }
    throw new Error(`[${endpoint}] ${errorDetail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getBaseUrl(): string {
    return apiConfig.getBaseUrl();
  },

  getConfigError(): string | null {
    return apiConfig.getConfigError();
  },

  getToken(): string | null {
    return memoryToken || (typeof localStorage !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null);
  },

  setToken(token: string | null) {
    memoryToken = token;
    try {
      if (token) {
        localStorage.setItem(TOKEN_KEY, token);
      } else {
        localStorage.removeItem(TOKEN_KEY);
      }
    } catch {
      // ignore
    }
  },

  clearToken() {
    this.setToken(null);
  },

  // -----------------------------------------------------------------------
  // SAAS AUTHENTICATION ENDPOINTS
  // -----------------------------------------------------------------------

  async signup(email: string, password: string, fullName: string = 'LifeOS Operator'): Promise<TokenResponse> {
    const url = apiConfig.buildUrl('/api/auth/signup');
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    const data = await handleResponse<TokenResponse>(res, '/api/auth/signup');
    if (data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const url = apiConfig.buildUrl('/api/auth/login');
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await handleResponse<TokenResponse>(res, '/api/auth/login');
    if (data.access_token) {
      this.setToken(data.access_token);
    }
    return data;
  },

  async getMe(): Promise<User> {
    const url = apiConfig.buildUrl('/api/auth/me');
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<User>(res, '/api/auth/me');
  },

  async logout(): Promise<void> {
    const url = apiConfig.buildUrl('/api/auth/logout');
    try {
      await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
    } catch {
      // ignore
    } finally {
      this.clearToken();
    }
  },

  async rotateOmiToken(): Promise<{ success: boolean; omi_webhook_token: string }> {
    const url = apiConfig.buildUrl('/api/auth/rotate-omi-token');
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse<{ success: boolean; omi_webhook_token: string }>(res, '/api/auth/rotate-omi-token');
  },

  async updateProfile(fullName?: string, telegramChatId?: string): Promise<User> {
    const url = apiConfig.buildUrl('/api/auth/profile');
    const res = await fetch(url, {
      method: 'PUT',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ full_name: fullName, telegram_chat_id: telegramChatId }),
    });
    return handleResponse<User>(res, '/api/auth/profile');
  },

  // -----------------------------------------------------------------------
  // SAAS INTEGRATIONS WIZARD ENDPOINTS
  // -----------------------------------------------------------------------

  async listIntegrations(): Promise<UserIntegrationsResponse> {
    const url = apiConfig.buildUrl('/api/integrations');
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<UserIntegrationsResponse>(res, '/api/integrations');
  },

  async saveIntegration(integrationType: string, credentials: Record<string, any>): Promise<IntegrationStatusItem> {
    const url = apiConfig.buildUrl(`/api/integrations/${encodeURIComponent(integrationType)}`);
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ credentials }),
    });
    return handleResponse<IntegrationStatusItem>(res, `/api/integrations/${integrationType}`);
  },

  async testIntegration(integrationType: string): Promise<{ success: boolean; message?: string }> {
    const url = apiConfig.buildUrl(`/api/integrations/${encodeURIComponent(integrationType)}/test`);
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse<{ success: boolean; message?: string }>(res, `/api/integrations/${integrationType}/test`);
  },

  async disconnectIntegration(integrationType: string): Promise<{ success: boolean; message: string }> {
    const url = apiConfig.buildUrl(`/api/integrations/${encodeURIComponent(integrationType)}`);
    const res = await fetch(url, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse<{ success: boolean; message: string }>(res, `/api/integrations/${integrationType}`);
  },

  async getOmiWebhookInfo(): Promise<OmiWebhookInfo> {
    const url = apiConfig.buildUrl('/api/integrations/omi/webhook-info');
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<OmiWebhookInfo>(res, '/api/integrations/omi/webhook-info');
  },

  // -----------------------------------------------------------------------
  // HEALTH & EXISTING DOMAIN ENDPOINTS
  // -----------------------------------------------------------------------

  async getHealth(): Promise<HealthResponse> {
    const url = apiConfig.buildUrl('/health');
    const res = await fetch(url);
    return handleResponse<HealthResponse>(res, '/health');
  },

  async listMemories(uid: string, limit: number = 50): Promise<MemoryItem[]> {
    const params = new URLSearchParams({
      uid: uid.trim(),
      limit: String(limit),
    });
    const url = apiConfig.buildUrl(`/api/memories?${params.toString()}`);
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<MemoryItem[]>(res, '/api/memories');
  },

  async searchMemories(req: MemorySearchRequest): Promise<MemorySearchResponse> {
    const url = apiConfig.buildUrl('/api/memories/search');
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(req),
    });
    return handleResponse<MemorySearchResponse>(res, '/api/memories/search');
  },

  async createMemory(req: MemoryCreateRequest): Promise<MemoryItem> {
    const url = apiConfig.buildUrl('/api/memories');
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(req),
    });
    return handleResponse<MemoryItem>(res, '/api/memories');
  },

  async deleteMemory(memoryId: string, uid: string): Promise<{ status: string; memory_id: string; uid: string }> {
    const url = apiConfig.buildUrl(`/api/memories/${encodeURIComponent(memoryId)}?uid=${encodeURIComponent(uid)}`);
    const res = await fetch(url, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse<{ status: string; memory_id: string; uid: string }>(res, `/api/memories/${memoryId}`);
  },

  async askAgent(req: AskRequest): Promise<AskResponse> {
    const url = apiConfig.buildUrl('/api/agents/ask');
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(req),
    });
    return handleResponse<AskResponse>(res, '/api/agents/ask');
  },

  async planDay(req: PlanRequest): Promise<PlanResponse> {
    const url = apiConfig.buildUrl('/api/lifeos/plan');
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(req),
    });
    return handleResponse<PlanResponse>(res, '/api/lifeos/plan');
  },

  async draftEmail(req: { uid: string; prompt: string; recipient?: string }): Promise<any> {
    const url = apiConfig.buildUrl('/api/lifeos/draft');
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(req),
    });
    return handleResponse<any>(res, '/api/lifeos/draft');
  },

  async listActions(uid: string): Promise<StagedAction[]> {
    const url = apiConfig.buildUrl(`/api/actions?uid=${encodeURIComponent(uid.trim())}`);
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<StagedAction[]>(res, '/api/actions');
  },

  async confirmAction(actionId: string, uid: string): Promise<ActionExecutionResponse> {
    const url = apiConfig.buildUrl(`/api/actions/${encodeURIComponent(actionId)}/confirm?uid=${encodeURIComponent(uid.trim())}`);
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse<ActionExecutionResponse>(res, `/api/actions/${actionId}/confirm`);
  },

  async rejectAction(actionId: string, uid: string): Promise<StagedAction> {
    const url = apiConfig.buildUrl(`/api/actions/${encodeURIComponent(actionId)}/reject?uid=${encodeURIComponent(uid.trim())}`);
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse<StagedAction>(res, `/api/actions/${actionId}/reject`);
  },

  async getLifeOSStatus(): Promise<LifeOSStatusResponse> {
    const url = apiConfig.buildUrl('/api/lifeos/status');
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<LifeOSStatusResponse>(res, '/api/lifeos/status');
  },

  async listNotifications(limit: number = 30): Promise<any[]> {
    const url = apiConfig.buildUrl(`/api/notifications?limit=${limit}`);
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<any[]>(res, '/api/notifications');
  },

  async testNotification(uid: string, message: string, chatId?: string): Promise<any> {
    const url = apiConfig.buildUrl('/api/notifications/test');
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ uid, message, chat_id: chatId }),
    });
    return handleResponse<any>(res, '/api/notifications/test');
  },

  async listWorkflows(uid?: string, limit: number = 30): Promise<WorkflowRecord[]> {
    const query = uid ? `?uid=${encodeURIComponent(uid.trim())}&limit=${limit}` : `?limit=${limit}`;
    const url = apiConfig.buildUrl(`/api/workflows${query}`);
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<WorkflowRecord[]>(res, '/api/workflows');
  },

  async getLatestWorkflow(uid?: string): Promise<WorkflowRecord | null> {
    const query = uid ? `?uid=${encodeURIComponent(uid.trim())}` : '';
    const url = apiConfig.buildUrl(`/api/workflows/latest${query}`);
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<WorkflowRecord | null>(res, '/api/workflows/latest');
  },

  async getWorkflowDetails(workflowId: string): Promise<WorkflowRecord> {
    const url = apiConfig.buildUrl(`/api/workflows/${encodeURIComponent(workflowId)}`);
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<WorkflowRecord>(res, `/api/workflows/${workflowId}`);
  },

  async getTelegramStatus(): Promise<any> {
    const url = apiConfig.buildUrl('/api/telegram/status');
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse<any>(res, '/api/telegram/status');
  },

  async simulateVoiceInput(uid: string, text: string): Promise<any> {
    const url = apiConfig.buildUrl(`/omi/conversation?uid=${encodeURIComponent(uid.trim())}`);
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        id: `sim-${Date.now()}`,
        transcript_segments: [{ text: text.trim(), speaker: 'user' }],
      }),
    });
    return handleResponse<any>(res, '/omi/conversation');
  },

  getEventSourceUrl(uid?: string): string {
    const params: Record<string, string> = {};
    const token = this.getToken();
    if (token) params['token'] = token;
    if (uid) params['uid'] = uid;
    return apiConfig.buildSSEUrl('/api/lifeos/events', params);
  },
};
