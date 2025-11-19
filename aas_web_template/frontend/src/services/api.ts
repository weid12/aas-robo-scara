import type { RobotState, RobotSummary } from "../types/robot";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Falha ao buscar ${path}`);
  }
  return (await response.json()) as T;
}

export function getLatestState(): Promise<RobotState> {
  return request<RobotState>("/api/robot/state/latest");
}

export function getHistory(limit = 50): Promise<RobotState[]> {
  return request<RobotState[]>(`/api/robot/state/history?limit=${limit}`);
}

export function getSummaryMetrics(): Promise<RobotSummary> {
  return request<RobotSummary>("/api/robot/metrics/summary");
}
