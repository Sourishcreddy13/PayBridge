export type PaymentState = 'PENDING' | 'PROCESSING' | 'SETTLED' | 'FAILED' | 'REFUNDED';
export type Rail = 'UPI' | 'NEFT' | 'RTGS' | 'IMPS';

export interface PaymentListItem { payment_id: string; state: PaymentState; amount: string; currency: string; rail: Rail | null; created_at: string; }
export interface OpsSummary { volumes_by_rail: Record<string, number>; volumes_by_status: Record<string, number>; unmatched_queue: unknown[]; refund_queue: unknown[]; }
