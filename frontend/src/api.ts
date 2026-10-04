import type { OpsSummary, PaymentListItem } from './types';

const TOKEN = import.meta.env.VITE_API_TOKEN ?? 'ops-demo-token';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}`, ...(init?.headers ?? {}) } });
  if (!response.ok) throw new Error(`request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export const api = {
  payments: () => request<PaymentListItem[]>('/api/v1/payments'),
  summary: () => request<OpsSummary>('/api/v1/ops/summary'),
  health: () => request<{ status: string }>('/health'),
};
