import { useState } from 'react';

export function SignIn({ onSubmit, error }: { onSubmit: (token: string) => void; error: string }) {
  const [value, setValue] = useState('');
  return <main className="shell narrow">
    <header className="header"><div><p className="eyebrow">PAYBRIDGE</p><h1>Sign in</h1></div></header>
    {error && <div className="error" role="alert">{error}</div>}
    <form className="panel form" onSubmit={(e) => { e.preventDefault(); onSubmit(value.trim()); }}>
      <label>Access token
        <input type="password" autoComplete="off" value={value} onChange={(e) => setValue(e.target.value)} required />
      </label>
      <button type="submit" className="primary">Sign in</button>
      <p className="hint">Tokens are issued by your administrator. Nothing is stored beyond this browser session.</p>
    </form>
  </main>;
}
