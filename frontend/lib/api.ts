/**
 * Typed API Client
 * All API calls go through this client. Automatically attaches the Authorization
 * header and handles token refresh on 401 responses.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    message?: string
  ) {
    super(message || detail);
    this.name = 'ApiError';
  }
}

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const { skipAuth = false, ...init } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  };

  // Attach access token from localStorage
  if (!skipAuth) {
    const token = localStorage.getItem('access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const response = await fetch(url, { ...init, headers, credentials: 'include' });

  // Attempt token refresh on 401
  if (response.status === 401 && !skipAuth && path !== '/api/v1/auth/login') {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      // Retry the original request with the new token
      return apiFetch<T>(path, { ...options, skipAuth: false });
    } else {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
      throw new ApiError(401, 'Session expired. Please log in again.');
    }
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ message: 'Unknown error' }));
    throw new ApiError(
      response.status,
      errorBody.detail || errorBody.message || `HTTP ${response.status}`,
    );
  }

  if (response.status === 204) return undefined as T;

  return response.json();
}

async function tryRefreshToken(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    if (!res.ok) return false;
    const data = await res.json();
    localStorage.setItem('access_token', data.access_token);
    return true;
  } catch {
    return false;
  }
}

// ─── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
  organization: Organization;
}

export interface User {
  id: string;
  org_id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'analyst' | 'viewer';
  is_active: boolean;
  mfa_enabled: boolean;
  last_login: string | null;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  is_active: boolean;
  created_at: string;
}

export const authApi = {
  login: (email: string, password: string) =>
    apiFetch<AuthResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    }),

  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    org: { name: string; slug: string };
  }) =>
    apiFetch<AuthResponse>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuth: true,
    }),

  logout: () =>
    apiFetch<void>('/api/v1/auth/logout', { method: 'POST' }),

  getProfile: () => apiFetch<User>('/api/v1/settings/profile'),
};

// ─── Dashboard ─────────────────────────────────────────────────────────────────

export interface DashboardStats {
  total_alerts: number;
  open_alerts: number;
  critical_alerts: number;
  total_threats: number;
  total_vulnerabilities: number;
  open_vulnerabilities: number;
  total_assets: number;
  logs_last_24h: number;
  flagged_logs: number;
  risk_score_avg: number;
}

export interface AlertTrend {
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface ThreatDistribution {
  threat_type: string;
  count: number;
}

export const dashboardApi = {
  getStats: () => apiFetch<DashboardStats>('/api/v1/dashboard/stats'),
  getAlertTrends: (days = 7) => apiFetch<AlertTrend[]>(`/api/v1/dashboard/alert-trends?days=${days}`),
  getThreatDistribution: () => apiFetch<ThreatDistribution[]>('/api/v1/dashboard/threat-distribution'),
};

// ─── Alerts ────────────────────────────────────────────────────────────────────

export interface Alert {
  id: string;
  org_id: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  status: 'open' | 'investigating' | 'resolved' | 'false_positive';
  alert_type: string;
  source_ip: string | null;
  dest_ip: string | null;
  mitre_tactic: string | null;
  mitre_technique: string | null;
  risk_score: number;
  ai_summary: string | null;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface AlertListResponse {
  items: Alert[];
  total: number;
  page: number;
  page_size: number;
}

export const alertsApi = {
  list: (params?: { page?: number; page_size?: number; severity?: string; status?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set('page', String(params.page));
    if (params?.page_size) q.set('page_size', String(params.page_size));
    if (params?.severity) q.set('severity', params.severity);
    if (params?.status) q.set('status', params.status);
    if (params?.search) q.set('search', params.search);
    return apiFetch<AlertListResponse>(`/api/v1/alerts?${q}`);
  },
  get: (id: string) => apiFetch<Alert>(`/api/v1/alerts/${id}`),
  create: (payload: Partial<Alert>) =>
    apiFetch<Alert>('/api/v1/alerts', { method: 'POST', body: JSON.stringify(payload) }),
  update: (id: string, payload: Partial<Alert>) =>
    apiFetch<Alert>(`/api/v1/alerts/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) =>
    apiFetch<void>(`/api/v1/alerts/${id}`, { method: 'DELETE' }),
};

// ─── Logs ──────────────────────────────────────────────────────────────────────

export interface LogEntry {
  id: string;
  source: string;
  raw_log: string;
  parsed_data: Record<string, unknown> | null;
  log_type: string;
  severity: string;
  anomaly_score: number;
  ip_src: string | null;
  ip_dst: string | null;
  is_flagged: boolean;
  log_timestamp: string;
  ingested_at: string;
}

export const logsApi = {
  list: (params?: { page?: number; is_flagged?: boolean; source?: string }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set('page', String(params.page));
    if (params?.is_flagged !== undefined) q.set('is_flagged', String(params.is_flagged));
    if (params?.source) q.set('source', params.source);
    return apiFetch<{ items: LogEntry[]; total: number; page: number; page_size: number }>(`/api/v1/logs?${q}`);
  },
  ingest: (payload: Partial<LogEntry> & { source: string; raw_log: string }) =>
    apiFetch<LogEntry>('/api/v1/logs/ingest', { method: 'POST', body: JSON.stringify(payload) }),
};

// ─── Threats ───────────────────────────────────────────────────────────────────

export interface ThreatIndicator {
  id: string;
  indicator_type: string;
  value: string;
  threat_type: string;
  confidence_score: number;
  abuse_confidence: number;
  source: string;
  country_code: string | null;
  is_active: boolean;
  first_seen: string;
  last_seen: string;
}

export const threatsApi = {
  list: (params?: { page?: number; indicator_type?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set('page', String(params.page));
    if (params?.indicator_type) q.set('indicator_type', params.indicator_type);
    if (params?.search) q.set('search', params.search);
    return apiFetch<{ items: ThreatIndicator[]; total: number; page: number; page_size: number }>(`/api/v1/threats?${q}`);
  },
  create: (payload: Partial<ThreatIndicator>) =>
    apiFetch<ThreatIndicator>('/api/v1/threats', { method: 'POST', body: JSON.stringify(payload) }),
  lookup: (value: string) =>
    apiFetch<ThreatIndicator | null>(`/api/v1/threats/lookup?value=${encodeURIComponent(value)}`),
};

// ─── Vulnerabilities ───────────────────────────────────────────────────────────

export interface Vulnerability {
  id: string;
  cve_id: string | null;
  title: string;
  description: string;
  cvss_score: number;
  severity: string;
  status: string;
  affected_software: string | null;
  patch_available: boolean;
  exploit_available: boolean;
  discovered_at: string;
}

export const vulnsApi = {
  list: (params?: { page?: number; severity?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set('page', String(params.page));
    if (params?.severity) q.set('severity', params.severity);
    if (params?.status) q.set('status', params.status);
    return apiFetch<{ items: Vulnerability[]; total: number; page: number; page_size: number }>(`/api/v1/vulnerabilities?${q}`);
  },
  delete: (id: string) =>
    apiFetch<void>(`/api/v1/vulnerabilities/${id}`, { method: 'DELETE' }),
};

// ─── Assets ────────────────────────────────────────────────────────────────────

export interface Asset {
  id: string;
  hostname: string;
  ip_address: string | null;
  os_type: string | null;
  asset_type: string;
  owner: string | null;
  risk_score: number;
  is_internet_facing: boolean;
  is_active: boolean;
  last_seen: string;
}

export const assetsApi = {
  list: (params?: { page?: number; asset_type?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set('page', String(params.page));
    if (params?.asset_type) q.set('asset_type', params.asset_type);
    if (params?.search) q.set('search', params.search);
    return apiFetch<{ items: Asset[]; total: number; page: number; page_size: number }>(`/api/v1/assets?${q}`);
  },
  create: (payload: Partial<Asset>) =>
    apiFetch<Asset>('/api/v1/assets', { method: 'POST', body: JSON.stringify(payload) }),
};

// ─── AI ────────────────────────────────────────────────────────────────────────

export interface AIResponse {
  session_id: string;
  message: string;
  timestamp: string;
  tokens_used: number | null;
}

export const aiApi = {
  chat: (content: string, session_id?: string, context_type = 'general') =>
    apiFetch<AIResponse>('/api/v1/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ content, session_id, context_type }),
    }),
  getConversations: () => apiFetch<{ session_id: string; title: string; updated_at: string }[]>('/api/v1/ai/conversations'),
  getConversation: (session_id: string) =>
    apiFetch<{ session_id: string; messages: { role: string; content: string; timestamp: string }[] }>(`/api/v1/ai/conversations/${session_id}`),
};

// ─── Reports ───────────────────────────────────────────────────────────────────

export interface Report {
  id: string;
  title: string;
  report_type: string;
  status: string;
  content: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
}

export const reportsApi = {
  list: () => apiFetch<Report[]>('/api/v1/reports'),
  create: (payload: { title: string; report_type: string; parameters?: Record<string, unknown> }) =>
    apiFetch<Report>('/api/v1/reports', { method: 'POST', body: JSON.stringify(payload) }),
  get: (id: string) => apiFetch<Report>(`/api/v1/reports/${id}`),
};

// ─── Notifications ─────────────────────────────────────────────────────────────

export interface NotificationItem {
  id: string;
  org_id: string;
  user_id: string | null;
  title: string;
  message: string;
  severity: string;
  is_read: boolean;
  link: string | null;
  created_at: string;
}

export const notificationsApi = {
  list: (params?: { page?: number; unread_only?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set('page', String(params.page));
    if (params?.unread_only) q.set('unread_only', 'true');
    return apiFetch<{ items: NotificationItem[]; unread_count: number; total: number; page: number; page_size: number }>(
      `/api/v1/notifications?${q}`
    );
  },
  markRead: (id: string) =>
    apiFetch<NotificationItem>(`/api/v1/notifications/${id}/read`, { method: 'PATCH' }),
  markAllRead: () =>
    apiFetch<{ message: string }>('/api/v1/notifications/mark-all-read', { method: 'POST' }),
};

// ─── Settings ──────────────────────────────────────────────────────────────────

export interface AuditLog {
  id: string;
  org_id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export const auditLogsApi = {
  list: (params?: { page?: number; action?: string; resource_type?: string; user_id?: string }) => {
    const q = new URLSearchParams();
    if (params?.page) q.set('page', String(params.page));
    if (params?.action) q.set('action', params.action);
    if (params?.resource_type) q.set('resource_type', params.resource_type);
    if (params?.user_id) q.set('user_id', params.user_id);
    return apiFetch<{ items: AuditLog[]; total: number; page: number; page_size: number }>(`/api/v1/audit-logs?${q}`);
  },
};

export const settingsApi = {
  getOrg: () => apiFetch<Organization>('/api/v1/settings/organization'),
  rotateApiKey: () =>
    apiFetch<{ api_key: string; message: string }>('/api/v1/settings/organization/rotate-api-key', { method: 'POST' }),
  getTeam: () => apiFetch<User[]>('/api/v1/settings/team'),
  addTeamMember: (payload: { email: string; full_name: string; role: string; password: string }) =>
    apiFetch<User>('/api/v1/settings/team', { method: 'POST', body: JSON.stringify(payload) }),
  updateMemberRole: (userId: string, role: string) =>
    apiFetch<{ id: string; role: string }>(`/api/v1/settings/team/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),
  updateMemberStatus: (userId: string, isActive: boolean) =>
    apiFetch<{ id: string; is_active: boolean }>(`/api/v1/settings/team/${userId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
    }),
  changePassword: (current_password: string, new_password: string) =>
    apiFetch<void>('/api/v1/settings/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),
};
