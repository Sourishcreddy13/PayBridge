import type { ReactNode } from 'react';

export function QueueCard({ title, count, description, children }: { title: string; count: number; description: string; children?: ReactNode }) {
  return <article className="queue-card" aria-label={`${title}`}>
    <div><span>{title}</span><strong>{count}</strong></div>
    <p>{description}</p>
    {children}
  </article>;
}
