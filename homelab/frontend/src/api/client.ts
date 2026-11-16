import {
  CollectorStatus,
  DashboardSummary,
  Device,
  HeartRateSample,
  RecoveryMetric,
  SleepSession,
  StrainMetric,
  Workout,
} from "../types";

const TOKEN_KEY = "noop_dashboard_token";
const DEFAULT_TOKEN = "changeme_dashboard_session_token";

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void) {
  unauthorizedHandler = handler;
}

export function getDashboardToken(): string {
  return localStorage.getItem(TOKEN_KEY) || DEFAULT_TOKEN;
}

export function setDashboardToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token.trim());
}

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getDashboardToken();
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = endpoint.startsWith("http") ? endpoint : `/api/v1${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    if (unauthorizedHandler) {
      unauthorizedHandler();
    }
    throw new Error("Dashboard authentication required (HTTP 401)");
  }

  if (!response.ok) {
    let detail = `Request failed: ${response.status} ${response.statusText}`;
    try {
      const err = await response.json();
      if (err.detail) detail = err.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  return response.json();
}

export const api = {
  getSummary: (deviceId?: string) =>
    apiFetch<DashboardSummary>(deviceId ? `/dashboard/summary?device_id=${encodeURIComponent(deviceId)}` : "/dashboard/summary"),

  getRecovery: (limit = 30) => apiFetch<RecoveryMetric[]>(`/recovery?limit=${limit}`),

  getStrain: (limit = 30) => apiFetch<StrainMetric[]>(`/strain?limit=${limit}`),

  getSleep: (limit = 30) => apiFetch<SleepSession[]>(`/sleep?limit=${limit}`),

  getHeartRate: (limit = 100) => apiFetch<HeartRateSample[]>(`/heart-rate?limit=${limit}`),

  getWorkouts: (limit = 30) => apiFetch<Workout[]>(`/workouts?limit=${limit}`),

  getCollectorStatus: () => apiFetch<CollectorStatus>("/collector/status"),

  getDevices: () => apiFetch<Device[]>("/devices"),
};
