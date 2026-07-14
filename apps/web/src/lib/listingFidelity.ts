import type { DataSource, SearchResultItem } from '@/api/types'

/** E20 ban list — never treat these hosts as listing photos. */
export const STOCK_IMAGE_HOST_PATTERNS = [
  'picsum.photos',
  'placeholder.com',
  'via.placeholder.com',
  'loremflickr.com',
  'placekitten.com',
  'placehold.co',
  'placehold.it',
  'dummyimage.com',
  'lorempixel.com',
  'images.unsplash.com',
  'source.unsplash.com',
  'unsplash.com',
] as const

/** Wire + alias; missing → non-live (honest default). */
export function resolveDataSource(property: {
  dataSource?: DataSource | null
  listingFidelity?: DataSource | null
}): DataSource {
  return property.dataSource ?? property.listingFidelity ?? 'demo_stub'
}

export function isLiveDataSource(ds: DataSource): boolean {
  return ds === 'live'
}

/** Badge when ≠ live (E17). */
export function dataSourceBadgeLabel(
  ds: DataSource,
): 'Demo' | 'Fixtures' | null {
  if (ds === 'live') return null
  if (ds === 'fixture_curated') return 'Fixtures'
  return 'Demo'
}

export function isValidPortalUrl(url?: string | null): boolean {
  if (!url?.trim()) return false
  try {
    const u = new URL(url.trim())
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return false
    if (!u.hostname) return false
    return true
  } catch {
    return false
  }
}

/**
 * E18 — CTA “Ver en portal”:
 * - demo_stub / missing → no
 * - live → yes if URL valid
 * - fixture_curated → yes only if URL looks valid (runtime fail → UX stub)
 */
export function canOpenPortalCta(opts: {
  dataSource: DataSource
  sourceUrl?: string | null
}): boolean {
  if (opts.dataSource === 'demo_stub') return false
  if (!isValidPortalUrl(opts.sourceUrl)) return false
  return opts.dataSource === 'live' || opts.dataSource === 'fixture_curated'
}

export function isStockImageUrl(url: string): boolean {
  try {
    const host = new URL(url).hostname.toLowerCase()
    return STOCK_IMAGE_HOST_PATTERNS.some(
      (p) => host === p || host.endsWith(`.${p}`) || host.includes(p),
    )
  } catch {
    return false
  }
}

export function hasNonLiveResults(
  items: Array<Pick<SearchResultItem, 'dataSource'> & { listingFidelity?: DataSource }>,
  densityHint?: string | null,
): boolean {
  if (densityHint && densityHint !== 'live') return true
  return items.some((item) => !isLiveDataSource(resolveDataSource(item)))
}
