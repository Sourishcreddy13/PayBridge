export type PaymentState = 'PENDING' | 'PROCESSING' | 'SETTLED' | 'FAILED' | 'REFUNDED';
export type Rail = 'UPI' | 'NEFT' | 'RTGS' | 'IMPS';
export type Role = 'CUSTOMER' | 'OPS' | 'ADMIN';
export type BeneficiaryType = 'RETAIL' | 'CORPORATE';
export type RefundStatus = 'PENDING' | 'COMPLETED' | 'FAILED';

export interface Identity { subject: string; role: Role; }
export interface PaymentListItem { payment_id: string; state: PaymentState; amount: string; currency: string; rail: Rail | null; created_at: string; }
export interface PaymentView extends PaymentListItem {
  narration: string; beneficiary_name: string; masked_account_number: string; masked_ifsc: string; reason_code: string | null;
}
export interface Transition { payment_id: string; from_state: PaymentState; to_state: PaymentState; at: string; actor: string; reason_code: string | null; reason: string | null; }
export interface RefundView { refund_id: string; original_payment_id: string; reverse_payment_id: string; amount: string; status: RefundStatus; requested_at: string; }
export interface SettlementLine { external_reference: string; payment_id: string | null; amount: string; currency: string; status: string; }
export interface QueuedPayment { payment_id: string; rail: Rail | null; amount: string; created_at: string; }
export interface OpsSummary {
  business_date: string;
  payments_today: number;
  volumes_by_rail: Record<string, number>;
  volumes_by_status: Record<string, number>;
  unmatched_queue: SettlementLine[];
  refund_queue: RefundView[];
  pending_queue: QueuedPayment[];
  retry_queue: QueuedPayment[];
}
export interface NewPayment {
  beneficiary: { name: string; account_number: string; ifsc: string; beneficiary_type: BeneficiaryType };
  amount: string; narration: string; idempotency_key: string; urgent: boolean;
}
