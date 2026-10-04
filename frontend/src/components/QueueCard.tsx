export function QueueCard({ title, count, description }: { title: string; count: number; description: string }) {
  return <article className="queue-card"><div><span>{title}</span><strong>{count}</strong></div><p>{description}</p></article>;
}
