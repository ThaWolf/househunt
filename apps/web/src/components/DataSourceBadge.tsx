import type { DataSource } from '@/api/types'
import { dataSourceBadgeLabel } from '@/lib/listingFidelity'

type Props = {
  dataSource: DataSource
  className?: string
}

/** E17 — badge when dataSource ≠ live. */
export function DataSourceBadge({ dataSource, className = '' }: Props) {
  const label = dataSourceBadgeLabel(dataSource)
  if (!label) return null

  const title =
    dataSource === 'fixture_curated'
      ? 'Resultado de fixtures / demo curado — no es scrap live de esta búsqueda'
      : 'Aviso demo / stub — no hay publicación real verificable'

  return (
    <span
      className={`rounded px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide bg-warn/15 text-warn border border-warn/30 ${className}`}
      title={title}
      data-testid="data-source-badge"
    >
      {label}
    </span>
  )
}
