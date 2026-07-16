import type { InterestItem } from '@/api/types'

export const AMENITY_LEGEND =
  '✓ confirmado · ? sin dato (no implica ausencia)'

export const AMENITY_UNKNOWN_TOOLTIP =
  'Sin dato confirmado — no implica que no tenga'

type Props = {
  items: InterestItem['amenitiesHighlight']
}

export function AmenityCell({ items }: Props) {
  if (!items?.length) {
    return <span className="text-ink-muted">—</span>
  }
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((a) => (
        <span
          key={a.token}
          title={a.present ? a.label : AMENITY_UNKNOWN_TOOLTIP}
          className={`inline-flex items-center rounded px-1 py-0.5 font-mono text-[10px] ${
            a.present
              ? 'bg-accent-soft text-accent'
              : 'border border-dashed border-line bg-paper text-ink-muted'
          }`}
        >
          {a.present ? '✓' : '?'} {a.label}
        </span>
      ))}
    </div>
  )
}
