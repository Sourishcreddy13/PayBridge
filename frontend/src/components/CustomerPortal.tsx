import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { BeneficiaryType, PaymentListItem, PaymentView, RefundView, Transition } from '../types';
import { PaymentTable } from './PaymentTable';

const emptyForm = { name: '', account_number: '', ifsc: '', beneficiary_type: 'RETAIL' as BeneficiaryType, amount: '', narration: '', urgent: false };
const newKey = () => `web-${crypto.randomUUID()}`;
const message = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

export function CustomerPortal() {
  const [payments, setPayments] = useState<PaymentListItem[]>([]);
  const [form, setForm] = useState(emptyForm);
  // One key per form attempt: resubmitting after a timeout replays instead of paying twice.
  const [key, setKey] = useState(newKey);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [selected, setSelected] = useState<PaymentView | null>(null);
  const [timeline, setTimeline] = useState<Transition[]>([]);
  const [refund, setRefund] = useState<RefundView | null>(null);

  const reload = useCallback(() => api.payments().then(setPayments).catch((e) => setError(message(e))), []);
  useEffect(() => { void reload(); }, [reload]);

  const open = useCallback(async (id: string) => {
    setError('');
    try {
      const [view, steps] = await Promise.all([api.payment(id), api.timeline(id)]);
      setSelected(view); setTimeline(steps);
      setRefund(await api.refundFor(id).catch(() => null));
    } catch (e) { setError(message(e)); }
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true); setError(''); setNotice('');
    try {
      const created = await api.createPayment({
        beneficiary: { name: form.name, account_number: form.account_number, ifsc: form.ifsc.toUpperCase(), beneficiary_type: form.beneficiary_type },
        amount: form.amount, narration: form.narration, idempotency_key: key, urgent: form.urgent,
      });
      setNotice(`Payment ${created.payment_id.slice(0, 8)} created and routed via ${created.rail ?? 'pending rail'}.`);
      setForm(emptyForm); setKey(newKey());
      await reload(); await open(created.payment_id);
    } catch (e) { setError(message(e)); } finally { setBusy(false); }
  }

  async function askRefund() {
    if (!selected) return;
    setError('');
    try { setRefund(await api.requestRefund(selected.payment_id)); await reload(); await open(selected.payment_id); } catch (e) { setError(message(e)); }
  }

  const set = <K extends keyof typeof emptyForm>(field: K, value: (typeof emptyForm)[K]) => setForm((f) => ({ ...f, [field]: value }));

  return <>
    {error && <div className="error" role="alert">{error}</div>}
    {notice && <div className="notice" role="status">{notice}</div>}
    <section className="panel" aria-labelledby="new-payment">
      <div className="panel-head"><h2 id="new-payment">New payment</h2><span>INR only</span></div>
      <form className="form grid" onSubmit={submit}>
        <label>Beneficiary name<input value={form.name} onChange={(e) => set('name', e.target.value)} required maxLength={100} /></label>
        <label>Account number<input inputMode="numeric" pattern="[0-9]{8,18}" value={form.account_number} onChange={(e) => set('account_number', e.target.value)} required /></label>
        <label>IFSC<input value={form.ifsc} onChange={(e) => set('ifsc', e.target.value)} required minLength={11} maxLength={11} /></label>
        <label>Beneficiary type<select value={form.beneficiary_type} onChange={(e) => set('beneficiary_type', e.target.value as BeneficiaryType)}><option value="RETAIL">Retail</option><option value="CORPORATE">Corporate</option></select></label>
        <label>Amount (₹)<input inputMode="decimal" value={form.amount} onChange={(e) => set('amount', e.target.value)} required /></label>
        <label>Narration<input value={form.narration} onChange={(e) => set('narration', e.target.value)} required maxLength={250} /></label>
        <label className="check"><input type="checkbox" checked={form.urgent} onChange={(e) => set('urgent', e.target.checked)} /> Urgent</label>
        <button type="submit" className="primary" disabled={busy}>{busy ? 'Submitting…' : 'Initiate payment'}</button>
      </form>
    </section>

    <section className="panel" aria-labelledby="my-payments">
      <div className="panel-head"><h2 id="my-payments">Payment history</h2><span>{payments.length} payments</span></div>
      <div className="table-wrap"><PaymentTable payments={payments} onSelect={(id) => void open(id)} selectedId={selected?.payment_id} /></div>
    </section>

    {selected && <section className="panel detail" aria-labelledby="payment-detail">
      <div className="panel-head"><h2 id="payment-detail">Payment {selected.payment_id.slice(0, 8)}</h2><span className={`status ${selected.state.toLowerCase()}`}>{selected.state}</span></div>
      <dl className="facts">
        <div><dt>Amount</dt><dd>{selected.currency} {selected.amount}</dd></div>
        <div><dt>Rail</dt><dd>{selected.rail ?? '—'}</dd></div>
        <div><dt>Beneficiary</dt><dd>{selected.beneficiary_name} · {selected.masked_account_number} · {selected.masked_ifsc}</dd></div>
        <div><dt>Narration</dt><dd>{selected.narration}</dd></div>
        {selected.state === 'FAILED' && <div><dt>Failure reason</dt><dd data-testid="reason-code">{selected.reason_code}</dd></div>}
      </dl>
      <h3>Timeline</h3>
      {timeline.length === 0 ? <p className="empty">Awaiting processing.</p> : <ol className="timeline">
        {timeline.map((t, i) => <li key={i}><strong>{t.from_state} → {t.to_state}</strong><span>{new Date(t.at).toLocaleString()} · {t.actor}{t.reason_code ? ` · ${t.reason_code}` : ''}</span></li>)}
      </ol>}
      <div className="actions">
        {selected.state === 'SETTLED' && !refund && <button onClick={() => void askRefund()}>Request full refund</button>}
        {refund && <p data-testid="refund-status">Refund {refund.status.toLowerCase()} · reverse entry {refund.reverse_payment_id.slice(0, 8)}</p>}
      </div>
    </section>}
  </>;
}
