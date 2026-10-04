export function MetricCard({ title, value, detail }: { title: string; value: string; detail: string }) {
  return <article className="metric" aria-label={`${title} metric`}><span>{title}</span><strong>{value}</strong><small>{detail}</small></article>;
}
