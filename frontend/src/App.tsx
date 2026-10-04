import { useEffect, useState } from 'react';
import { api } from './api';
import type { OpsSummary, PaymentListItem } from './types';
import { PaymentTable } from './components/PaymentTable';
import { MetricCard } from './components/MetricCard';
import { QueueCard } from './components/QueueCard';

export function App() {
  const [payments, setPayments] = useState<PaymentListItem[]>([]);
  const [summary, setSummary] = useState<OpsSummary | null>(null);
  const [health, setHealth] = useState('checking');
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.payments(), api.summary(), api.health()]).then(([p, s, h]) => {
      setPayments(p); setSummary(s); setHealth(h.status);
    }).catch((err: Error) => setError(err.message));
  }, []);

  return <main className="shell">
    <header className="header"><div><p className="eyebrow">PAYBRIDGE</p><h1>Payments operations hub</h1></div><span className="health">API {health}</span></header>
    {error && <div className="error" role="alert">{error}</div>}
    <section className="metrics">
      <MetricCard title="Today" value={String(payments.length)} detail="payments" />
      <MetricCard title="Settled" value={String(summary?.volumes_by_status.SETTLED ?? 0)} detail="payments" />
      <MetricCard title="Unmatched" value={String(summary?.unmatched_queue.length ?? 0)} detail="settlement items" />
      <MetricCard title="Refunds" value={String(summary?.refund_queue.length ?? 0)} detail="reverse entries" />
    </section>
    <section className="queue-grid">
      <QueueCard title="Unmatched queue" count={summary?.unmatched_queue.length ?? 0} description="Settlement items requiring ops review." />
      <QueueCard title="Refund queue" count={summary?.refund_queue.length ?? 0} description="Reverse entries recorded today or earlier." />
    </section>
    <section className="panel"><div className="panel-head"><h2>Payment history</h2><span>synthetic data</span></div><div className="table-wrap"><PaymentTable payments={payments} /></div></section>
  </main>;
}

