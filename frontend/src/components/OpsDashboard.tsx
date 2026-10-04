import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { OpsSummary, PaymentListItem } from '../types';
import { MetricCard } from './MetricCard';
import { PaymentTable } from './PaymentTable';
import { QueueCard } from './QueueCard';

const today = () => new Date().toISOString().slice(0, 10);
const message = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data);
  return <article className="queue-card" aria-label={title}>
    <div><span>{title}</span></div>
    {entries.length === 0 ? <p>No volume.</p> : <ul className="breakdown">{entries.map(([k, v]) => <li key={k}><span>{k}</span><strong>{v}</strong></li>)}</ul>}
  </article>;
}

export function OpsDashboard() {
  const [date, setDate] = useState(today);
  const [summary, setSummary] = useState<OpsSummary | null>(null);
  const [payments, setPayments] = useState<PaymentListItem[]>([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const reload = useCallback(async () => {
    try {
      const [s, p] = await Promise.all([api.summary(date), api.payments()]);
      setSummary(s); setPayments(p); setError('');
    } catch (e) { setError(message(e)); }
  }, [date]);
  useEffect(() => { void reload(); }, [reload]);

  async function act(label: string, run: () => Promise<unknown>) {
    setError(''); setNotice('');
    try { await run(); setNotice(label); await reload(); } catch (e) { setError(message(e)); }
  }

  const s = summary;
  return <>
    {error && <div className="error" role="alert">{error}</div>}
    {notice && <div className="notice" role="status">{notice}</div>}
    <section className="toolbar"><label>Business date<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label></section>
    <section className="metrics">
      <MetricCard title="Today" value={String(s?.payments_today ?? 0)} detail="payments created" />
      <MetricCard title="Settled" value={String(s?.volumes_by_status.SETTLED ?? 0)} detail="payments" />
      <MetricCard title="Unmatched" value={String(s?.unmatched_queue.length ?? 0)} detail="settlement items" />
      <MetricCard title="Refunds" value={String(s?.refund_queue.length ?? 0)} detail="requests" />
    </section>

    <section className="queue-grid">
      <Breakdown title="Volume by rail" data={s?.volumes_by_rail ?? {}} />
      <Breakdown title="Volume by status" data={s?.volumes_by_status ?? {}} />
    </section>

    <section className="queue-grid">
      <QueueCard title="Awaiting processing" count={s?.pending_queue.length ?? 0} description="PENDING payments an operator can submit to their rail.">
        <ul className="rows">{s?.pending_queue.map((q) => <li key={q.payment_id}><span>{q.payment_id.slice(0, 8)} · {q.rail} · ₹{q.amount}</span>
          <button onClick={() => void act(`Processed ${q.payment_id.slice(0, 8)}`, () => api.processPayment(q.payment_id))}>Process</button></li>)}</ul>
      </QueueCard>
      <QueueCard title="Retry queue" count={s?.retry_queue.length ?? 0} description="Payments left PROCESSING: submitted but not yet resolved.">
        <ul className="rows">{s?.retry_queue.map((q) => <li key={q.payment_id}><span>{q.payment_id.slice(0, 8)} · {q.rail} · ₹{q.amount}</span></li>)}</ul>
      </QueueCard>
      <QueueCard title="Unmatched queue" count={s?.unmatched_queue.length ?? 0} description="Settlement items requiring ops review.">
        <ul className="rows">{s?.unmatched_queue.map((u) => <li key={u.external_reference}><span>{u.external_reference} · ₹{u.amount}</span></li>)}</ul>
      </QueueCard>
      <QueueCard title="Refund queue" count={s?.refund_queue.length ?? 0} description="Refund requests and their outcome.">
        <ul className="rows">{s?.refund_queue.map((r) => <li key={r.refund_id}><span>{r.original_payment_id.slice(0, 8)} · ₹{r.amount} · {r.status}</span>
          {r.status === 'PENDING' && <span className="inline">
            <button onClick={() => void act('Refund approved', () => api.approveRefund(r.refund_id))}>Approve</button>
            <button onClick={() => void act('Refund rejected', () => api.rejectRefund(r.refund_id, 'Rejected by operations'))}>Reject</button></span>}</li>)}</ul>
      </QueueCard>
    </section>

    <section className="panel" aria-labelledby="settlement-ops">
      <div className="panel-head"><h2 id="settlement-ops">Settlement & reconciliation · {date}</h2></div>
      <div className="form actions-row">
        <label>Inbound settlement file (CSV)
          <input type="file" accept=".csv,text/csv" onChange={(e) => { const f = e.target.files?.[0]; if (f) void act(`Imported ${f.name}`, () => api.importSettlement(date, f)); e.target.value = ''; }} />
        </label>
        <button onClick={() => void act('Reconciliation complete', () => api.reconcile(date))}>Reconcile</button>
        <button onClick={() => void act('Settlement file generated', () => api.generateSettlement(date))}>Generate settlement</button>
      </div>
    </section>

    <section className="panel"><div className="panel-head"><h2>Payment history</h2><span>all payments</span></div><div className="table-wrap"><PaymentTable payments={payments} /></div></section>
  </>;
}
