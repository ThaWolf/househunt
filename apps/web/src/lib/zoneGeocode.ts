import type { GeocodeStatus, MapEmbed, ZoneReport } from '@/api/types'

export const WEAK_GEOCODE_MESSAGE =
  'No pudimos ubicar esta propiedad con precisión. El análisis de zona puede ser incompleto.'

const WEAK_STATUSES: GeocodeStatus[] = ['missing', 'approximate', 'stub']

export function isWeakGeocode(
  zoneReport?: ZoneReport | null,
  map?: MapEmbed | null,
): boolean {
  if (!zoneReport && !map) return true

  const status = zoneReport?.geo?.geocodeStatus
  if (!status || WEAK_STATUSES.includes(status)) return true

  const embedUrl = map?.embedUrl?.trim()
  if (map && !embedUrl && map.provider === 'external_only') return true

  return false
}
