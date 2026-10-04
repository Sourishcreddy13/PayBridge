import type { PaymentListItem } from '../types';

interface Props { payments: PaymentListItem[]; onSelect?: (id: string) => void; selectedId?: string | null; }

export function PaymentTable({ payments, onSelect, selectedId }: Props) {
  if (payments.length === 0) return <div className="empty">No payments for the selected day.</div>;
  return <table><thead><tr><th>Payment</th><th>Rail</th><th>Amount</th><th>Status</th><th>Created</th></tr></thead><tbody>
    {payments.map((p) => <tr key={p.payment_id} className={p.payment_id === selectedId ? 'selected' : undefined}>
      <td>{onSelect
        ? <button className="link" onClick={() => onSelect(p.payment_id)} aria-label={`Open payment ${p.payment_id.slice(0, 8)}`}>{p.payment_id.slice(0, 8)}</button>
        : p.payment_id.slice(0, 8)}</td>
      <td>{p.rail ?? '—'}</td><td>{p.currency} {p.amount}</td>
      <td><span className={`status ${p.state.toLowerCase()}`}>{p.state}</span></td>
      <td>{new Date(p.created_at).toLocaleString()}</td>
    </tr>)}
  </tbody></table>;
}
