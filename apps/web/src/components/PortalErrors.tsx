import type { PortalSearchResult } from '@/api/types'
import { PORTAL_LABELS } from '@/api/types'

export function PortalErrorsBanner({
  portalResults,
}: {
  portalResults: PortalSearchResult[]
}) {
  const issues = portalResults.filter(
    (p) => p.status === 'error' || p.status === 'partial' || p.status === 'skipped',
  )
  if (!issues.length) return null

  return (
    <div
      className="mb-4 rounded-md border border-warn/40 bg-amber-50 px-3 py-2 text-sm animate-fade-in"
      role="status"
    >
      <p className="font-medium text-warn mb-1">Resultados parciales por portal</p>
      <ul className="space-y-1 text-ink-muted">
        {issues.map((p) => (
          <li key={p.portal} className="font-mono text-xs">
            <span className="text-ink">{PORTAL_LABELS[p.portal]}</span>
            {' · '}
            {p.status}
            {p.diagnostics
              ? ` · raw ${p.diagnostics.rawCount}→${p.diagnostics.afterFilterCount}`
              : p.pagination?.listingsRaw != null
                ? ` · raw ${p.pagination.listingsRaw}→${p.pagination.listingsAfterFilter ?? '—'}`
                : null}
            {p.diagnostics?.roomsFilterWiped ? ' · rooms wipe' : null}
            {p.error ? ` — ${p.error.message}` : null}
            {p.unsupportedFilters?.length
              ? ` (filtros ignorados: ${p.unsupportedFilters.join(', ')})`
              : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
