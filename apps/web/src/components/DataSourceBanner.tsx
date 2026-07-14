import type { SearchResponse, SearchResultItem } from '@/api/types'
import { hasNonLiveResults } from '@/lib/listingFidelity'

type Props = {
  items: SearchResultItem[]
  density?: SearchResponse['density']
}

/** Results-level transparency when any item ≠ live (E17). */
export function DataSourceBanner({ items, density }: Props) {
  if (!hasNonLiveResults(items, density?.dataSourceHint ?? density?.mode)) {
    return null
  }

  const mode = density?.mode
  const hint = density?.dataSourceHint
  const detail =
    hint === 'fixture_curated' || mode === 'fixtures'
      ? 'Algunos o todos los resultados vienen de fixtures curados — no confundir con inventario live.'
      : hint === 'demo_stub'
        ? 'Hay avisos demo/stub: el CTA al portal está deshabilitado en esos casos.'
        : 'Hay resultados no-live (fixtures o demo). Revisá el badge en cada card.'

  return (
    <div
      className="mb-4 rounded-md border border-warn/40 bg-amber-50 px-3 py-2 text-sm animate-fade-in"
      role="status"
      data-testid="data-source-banner"
    >
      <p className="font-medium text-warn mb-0.5">Origen mixto / no-live</p>
      <p className="text-ink-muted text-xs">{detail}</p>
    </div>
  )
}
