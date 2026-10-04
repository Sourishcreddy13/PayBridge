import type { PaymentListItem } from '../types';

export function PaymentTable({ payments }: { payments: PaymentListItem[] }) {
  if (payments.length === 0) return <div className="empty">No payments for the selected day.</div>;
  return <table><thead><tr><th>Payment</th><th>Rail</th><th>Amount</th><th>Status</th><th>Created</th></tr></thead><tbody>
    {payments.map((p) => <tr key={p.payment_id}><td>{p.payment_id.slice(0, 8)}</td><td>{p.rail ?? '—'}</td><td>{p.currency} {p.amount}</td><td><span className={`status ${p.state.toLowerCase()}`}>{p.state}</span></td><td>{new Date(p.created_at).toLocaleString()}</td></tr>)}
  </tbody></table>;
}
