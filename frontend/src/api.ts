import type {
  Identity, NewPayment, OpsSummary, PaymentListItem, PaymentView, RefundView, Transition,
} from './types';

// No credential ships in the bundle. The bearer token is typed by the signed-in person and kept
// for the browser session only.
const STORAGE_KEY = 'paybridge.token';
let token = '';
try { token = sessionStorage.getItem(STORAGE_KEY) ?? ''; } catch { /* storage unavailable: memory only */ }

export function setToken(value: string): void {
  token = value;
  try { value ? sessionStorage.setItem(STORAGE_KEY, value) : sessionStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
}
export const hasToken = (): boolean => token !== '';

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

async function send(url: string, init: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}`, ...(init.headers as Record<string, string> | undefined) };
  const response = await fetch(url, { ...init, headers });
  if (!response.ok) {
    let detail = `request failed (${response.status})`;
    try { const body = await response.json() as { error?: string; detail?: unknown }; detail = body.error ?? (typeof body.detail === 'string' ? body.detail : detail); } catch { /* keep default */ }
    throw new ApiError(detail, response.status);
  }
  return response;
}
const json = async <T>(url: string, init?: RequestInit): Promise<T> => (await send(url, init)).json() as Promise<T>;
const post = <T>(url: string, body?: unknown): Promise<T> =>
  json<T>(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => fetch('/health').then((r) => r.json() as Promise<{ status: string }>),
  me: () => json<Identity>('/api/v1/me'),
  // customer
  payments: () => json<PaymentListItem[]>('/api/v1/payments'),
  payment: (id: string) => json<PaymentView>(`/api/v1/payments/${id}`),
  timeline: (id: string) => json<Transition[]>(`/api/v1/payments/${id}/timeline`),
  createPayment: (payment: NewPayment) => post<PaymentView>('/api/v1/payments', payment),
  requestRefund: (id: string) => post<RefundView>(`/api/v1/payments/${id}/refund`, {}),
  refundFor: (id: string) => json<RefundView>(`/api/v1/payments/${id}/refund`),
  // operations
  summary: (businessDate?: string) => json<OpsSummary>(`/api/v1/ops/summary${businessDate ? `?business_date=${businessDate}` : ''}`),
  processPayment: (id: string) => post<PaymentView>(`/api/v1/payments/${id}/process`),
  approveRefund: (id: string) => post<RefundView>(`/api/v1/refunds/${id}/approve`),
  rejectRefund: (id: string, reason: string) => post<RefundView>(`/api/v1/refunds/${id}/reject`, { reason }),
  reconcile: (date: string) => post<unknown[]>(`/api/v1/reconciliation/${date}`),
  generateSettlement: (date: string) => post<{ path: string }>('/api/v1/settlement', { business_date: date }),
  importSettlement: async (date: string, file: File) =>
    (await send(`/api/v1/settlement/import?business_date=${date}`, { method: 'POST', headers: { 'Content-Type': 'text/csv' }, body: await file.text() })).json() as Promise<{ entry_count: number }>,
};
