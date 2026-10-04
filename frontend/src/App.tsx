import { useCallback, useEffect, useState } from 'react';
import { api, hasToken, setToken } from './api';
import { CustomerPortal } from './components/CustomerPortal';
import { OpsDashboard } from './components/OpsDashboard';
import { SignIn } from './components/SignIn';
import type { Identity } from './types';

export function App() {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [health, setHealth] = useState('checking');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(hasToken());

  const signIn = useCallback(async (token: string) => {
    setToken(token); setError(''); setLoading(true);
    try { setIdentity(await api.me()); } catch { setToken(''); setError('That token was not accepted.'); } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    api.health().then((h) => setHealth(h.status)).catch(() => setHealth('DOWN'));
    if (hasToken()) api.me().then(setIdentity).catch(() => setToken('')).finally(() => setLoading(false));
  }, []);

  if (loading) return <main className="shell"><p className="empty">Loading…</p></main>;
  if (!identity) return <SignIn onSubmit={(t) => void signIn(t)} error={error} />;

  const staff = identity.role !== 'CUSTOMER';
  return <main className="shell">
    <header className="header">
      <div><p className="eyebrow">PAYBRIDGE</p><h1>{staff ? 'Payments operations hub' : 'My payments'}</h1></div>
      <div className="who"><span className="health">API {health}</span><span className="health">{identity.subject} · {identity.role}</span>
        <button onClick={() => { setToken(''); setIdentity(null); }}>Sign out</button></div>
    </header>
    {staff ? <OpsDashboard /> : <CustomerPortal />}
  </main>;
}
