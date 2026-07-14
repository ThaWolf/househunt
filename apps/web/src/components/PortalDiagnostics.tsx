import type { SearchResponse } from '@/api/types'
import { PORTAL_LABELS } from '@/api/types'
import { portalCountRows } from '@/lib/emptyState'

type Props = {
  response: Pick<SearchResponse, 'portalResults' | 'diagnostics'>
  /** Compact strip under results header when there are items. */
  compact?: boolean
}

/** Optional per-portal raw / afterFilter counts from diagnostics (E16/E23). */
export function PortalDiagnosticsStrip({ response, compact }: Props) {
  const rows = portalCountRows(response)
  const withCounts = rows.filter(
    (r) => r.rawCount != null || r.afterFilterCount != null,
  )
  if (!withCounts.length) return null

  return (
    <div
      className={
        compact
          ? 'mb-3 font-mono text-[11px] text-ink-muted'
          : 'mb-4 rounded-md border border-line bg-surface/60 px-3 py-2 text-xs'
      }
      data-testid="portal-diagnostics-strip"
      role="status"
    >
      {!compact ? (
        <p className="font-medium text-ink mb-1 text-sm">
          Conteos por portal
        </p>
      ) : null}
      <ul className="flex flex-wrap gap-x-3 gap-y-1">
        {withCounts.map((r) => (
          <li key={r.portal}>
            <span className="text-ink">{PORTAL_LABELS[r.portal]}</span>
            {': '}
            {r.rawCount ?? '—'}→{r.afterFilterCount ?? '—'}
            {r.roomsFilterWiped ? ' (wipe)' : ''}
          </li>
        ))}
      </ul>
    </div>
  )
}
