import { useId, useState } from 'react'
import { Link } from 'react-router-dom'
import type { SearchResponse } from '@/api/types'
import { PORTAL_LABELS } from '@/api/types'
import { portalCountRows, resolveEmptyState } from '@/lib/emptyState'

type Props = {
  response: Pick<
    SearchResponse,
    'items' | 'portalResults' | 'diagnostics' | 'filters'
  >
}

/** E23 — actionable empty panel when search returns 0 items (not a silent success). */
export function EmptyStatePanel({ response }: Props) {
  const empty = resolveEmptyState(response)
  const rows = portalCountRows(response)
  const diagId = useId()
  const [showDiag, setShowDiag] = useState(false)

  if (!empty) return null

  const hasAnyCounts = rows.some(
    (r) => r.rawCount != null || r.afterFilterCount != null,
  )

  return (
    <div
      className="rounded-lg border border-line bg-surface px-4 py-8 text-center animate-fade-in"
      role="status"
      data-testid="empty-state-panel"
      data-kind={empty.kind}
    >
      <h2 className="font-display text-2xl font-bold text-ink mb-2">
        {empty.title}
      </h2>
      <p className="text-sm text-ink-muted max-w-lg mx-auto mb-2">
        {empty.body}
      </p>
      {empty.hint ? (
        <p className="text-xs text-ink-muted max-w-md mx-auto mb-4">
          {empty.hint}
        </p>
      ) : (
        <div className="mb-4" />
      )}

      <div className="flex flex-wrap items-center justify-center gap-2 mb-4">
        <Link to="/search" className="hh-btn-accent no-underline text-sm">
          Ajustar filtros
        </Link>
        <Link to="/interest" className="hh-btn-ghost no-underline text-sm">
          Agregar publicación externa
        </Link>
        {hasAnyCounts || rows.length > 0 ? (
          <button
            type="button"
            className="hh-btn-ghost text-sm"
            aria-expanded={showDiag}
            aria-controls={diagId}
            onClick={() => setShowDiag((v) => !v)}
            data-testid="toggle-diagnostics"
          >
            {showDiag ? 'Ocultar diagnostics' : 'Ver diagnostics'}
          </button>
        ) : null}
      </div>

      {showDiag ? (
        <div
          id={diagId}
          className="mx-auto max-w-xl text-left rounded-md border border-line bg-canvas px-3 py-2"
          data-testid="diagnostics-panel"
        >
          {response.diagnostics ? (
            <p className="font-mono text-xs text-ink-muted mb-2">
              total raw {response.diagnostics.rawCount} → afterFilter{' '}
              {response.diagnostics.afterFilterCount}
              {response.diagnostics.roomsDropped
                ? ` · roomsDropped ${response.diagnostics.roomsDropped}`
                : ''}
              {response.diagnostics.roomsFilterWiped
                ? ' · roomsFilterWiped'
                : ''}
            </p>
          ) : null}
          <ul className="space-y-1">
            {rows.map((r) => (
              <li
                key={r.portal}
                className="font-mono text-xs text-ink-muted flex flex-wrap gap-x-2"
                data-testid={`diag-row-${r.portal}`}
              >
                <span className="text-ink">{PORTAL_LABELS[r.portal]}</span>
                <span>{r.status}</span>
                {r.rawCount != null || r.afterFilterCount != null ? (
                  <span>
                    raw {r.rawCount ?? '—'} → afterFilter{' '}
                    {r.afterFilterCount ?? '—'}
                  </span>
                ) : null}
                {r.roomsFilterWiped ? (
                  <span className="text-warn">rooms wipe</span>
                ) : null}
                {r.maturity ? <span>{r.maturity}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
