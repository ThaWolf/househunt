import type { MapEmbed, ZonePlace, ZoneReport } from '@/api/types'
import { isWeakGeocode, WEAK_GEOCODE_MESSAGE } from '@/lib/zoneGeocode'

type Props = {
  zoneReport?: ZoneReport | null
  map?: MapEmbed | null
}

function PlaceList({
  title,
  items,
}: {
  title: string
  items: ZonePlace[]
}) {
  if (items.length === 0) {
    return (
      <div>
        <h3 className="hh-label mb-1">{title}</h3>
        <p className="text-xs text-ink-muted">Sin datos</p>
      </div>
    )
  }
  return (
    <div>
      <h3 className="hh-label mb-1">{title}</h3>
      <ul className="space-y-1 text-sm text-ink-muted">
        {items.map((p) => (
          <li key={p.id}>
            <span className="text-ink">{p.name}</span>
            {p.category ? (
              <span className="ml-1 font-mono text-[10px] text-ink-muted">
                · {p.category}
              </span>
            ) : null}
            {p.distanceM != null ? (
              <span className="ml-1 font-mono text-[10px] text-ink-muted">
                · {Math.round(p.distanceM)} m
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ZoneMapBlock({ zoneReport, map }: Props) {
  const weakGeocode = isWeakGeocode(zoneReport, map)
  const embedUrl = map?.embedUrl?.trim() || null
  const externalUrl = map?.externalUrl?.trim() || null

  if (!zoneReport && !map) {
    return (
      <section
        className="rounded-lg border border-line bg-surface p-4 animate-fade-in"
        aria-label="Zona y mapa"
        data-testid="zone-map-block"
      >
        <h2 className="font-display text-xl font-semibold mb-2">Zona</h2>
        <p className="text-sm text-ink-muted" data-testid="weak-geocode-message">
          {WEAK_GEOCODE_MESSAGE}
        </p>
      </section>
    )
  }

  return (
    <section
      className="rounded-lg border border-line bg-surface p-4 space-y-4 animate-fade-in"
      aria-label="Zona y mapa"
      data-testid="zone-map-block"
    >
      <h2 className="font-display text-xl font-semibold">Zona</h2>

      {weakGeocode && (
        <p
          className="rounded border border-warn/30 bg-amber-50 px-3 py-2 text-sm text-warn"
          data-testid="weak-geocode-message"
        >
          {WEAK_GEOCODE_MESSAGE}
        </p>
      )}

      {zoneReport?.summary && (
        <p className="text-sm leading-relaxed text-ink-muted">
          {zoneReport.summary}
        </p>
      )}

      {zoneReport && (
        <div className="grid gap-4 sm:grid-cols-3">
          <PlaceList title="Puntos de interés" items={zoneReport.poi} />
          <PlaceList title="Comercios" items={zoneReport.commerce} />
          <PlaceList title="Transporte" items={zoneReport.transit} />
        </div>
      )}

      {map && (
        <div>
          <h3 className="hh-label mb-2">Mapa</h3>
          {embedUrl ? (
            <div className="overflow-hidden rounded-md border border-line bg-paper">
              <iframe
                title="Mapa de la propiedad"
                src={embedUrl}
                className="h-[280px] w-full border-0"
                loading="lazy"
                referrerPolicy="no-referrer-when-downgrade"
                allowFullScreen
              />
            </div>
          ) : (
            <p className="mb-2 text-sm text-ink-muted">
              Mapa embebido no disponible
              {map.provider === 'external_only'
                ? ' (Maps degradado).'
                : '.'}{' '}
              Abrí la ubicación en Google Maps.
            </p>
          )}
          {externalUrl && (
            <a
              href={externalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex hh-btn-ghost no-underline text-sm"
            >
              Abrir en Google Maps ↗
            </a>
          )}
        </div>
      )}
    </section>
  )
}
