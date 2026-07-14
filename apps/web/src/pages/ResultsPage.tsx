import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { SearchResponse } from '@/api/types'
import { DataSourceBanner } from '@/components/DataSourceBanner'
import { EmptyStatePanel } from '@/components/EmptyStatePanel'
import { PortalDiagnosticsStrip } from '@/components/PortalDiagnostics'
import { PortalErrorsBanner } from '@/components/PortalErrors'
import { PropertyCard } from '@/components/PropertyCard'
import { ErrorState } from '@/components/LoadingState'
import { LAST_SEARCH_KEY } from '@/pages/SearchPage'

export function ResultsPage() {
  const data = useMemo(() => {
    try {
      const raw = sessionStorage.getItem(LAST_SEARCH_KEY)
      if (!raw) return null
      return JSON.parse(raw) as SearchResponse
    } catch {
      return null
    }
  }, [])

  if (!data) {
    return (
      <ErrorState
        title="Sin resultados en sesión"
        message="Ejecutá una búsqueda primero."
      />
    )
  }

  const empty = data.items.length === 0

  return (
    <div className="animate-fade-in">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-4xl font-bold text-ink">Resultados</h1>
          <p className="text-sm text-ink-muted font-mono">
            {data.items.length} props · {data.tookMs} ms ·{' '}
            {data.filters.location
              ? data.filters.location.locality
              : 'GBA (preset)'}
            {data.filters.rooms?.min != null
              ? ` · ≥${data.filters.rooms.min} hab`
              : ''}
            {data.diagnostics?.roomsFilterWiped ? ' · rooms wipe' : ''}
          </p>
        </div>
        <Link to="/search" className="hh-btn-ghost no-underline text-sm">
          Nueva búsqueda
        </Link>
      </div>

      <PortalErrorsBanner portalResults={data.portalResults} />
      {!empty ? (
        <PortalDiagnosticsStrip response={data} compact />
      ) : null}
      <DataSourceBanner items={data.items} density={data.density} />

      {empty ? (
        <EmptyStatePanel response={data} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((item) => (
            <PropertyCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}
