import { Link } from 'react-router-dom'
import type { SearchResultItem } from '@/api/types'
import { PORTAL_LABELS } from '@/api/types'
import { AppScoreBadge } from '@/components/AppScoreBadge'
import { InterestBadge } from '@/components/InterestBadge'
import { formatLocation, formatMoney, primaryImageUrl } from '@/lib/format'

type Props = {
  item: SearchResultItem
}

export function PropertyCard({ item }: Props) {
  const img = primaryImageUrl(item.images)
  const badgeBlocked =
    item.interest?.state === 'active' || item.interest?.state === 'archived'

  return (
    <article className="hh-card flex flex-col animate-fade-in">
      <Link to={`/properties/${item.id}`} className="block no-underline text-inherit">
        <div className="relative aspect-[4/3] bg-line/60 overflow-hidden">
          {img ? (
            <img
              src={img}
              alt=""
              className="h-full w-full object-cover"
              loading="lazy"
              onError={(e) => {
                e.currentTarget.style.display = 'none'
              }}
            />
          ) : (
            <div className="flex h-full items-center justify-center font-mono text-xs text-ink-muted">
              Sin imagen
            </div>
          )}
          <div className="absolute left-2 top-2 flex flex-wrap gap-1">
            <InterestBadge interest={item.interest} />
          </div>
          <div className="absolute bottom-2 right-2">
            <AppScoreBadge score={item.appScore} size="sm" />
          </div>
        </div>
        <div className="p-3 flex flex-col gap-1.5">
          <p className="font-display text-lg leading-tight line-clamp-2 font-semibold text-ink">
            {item.title}
          </p>
          <p className="font-mono text-sm text-accent font-medium">
            {formatMoney(item.price)}
          </p>
          <p className="text-xs text-ink-muted line-clamp-1">
            {formatLocation(item.address)}
          </p>
          {item.descriptionExcerpt && (
            <p className="text-xs text-ink-muted line-clamp-2">
              {item.descriptionExcerpt}
            </p>
          )}
          <div className="flex items-center justify-between gap-2 pt-1">
            <span className="font-mono text-[10px] uppercase text-ink-muted">
              {PORTAL_LABELS[item.portal]}
              {item.rooms != null ? ` · ${item.rooms} amb` : ''}
            </span>
            {badgeBlocked && (
              <span className="text-[10px] text-ink-muted">ya en lista</span>
            )}
          </div>
        </div>
      </Link>
      <div className="border-t border-line px-3 py-2">
        <a
          href={item.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono text-[11px] text-accent no-underline hover:underline"
        >
          Ver en portal ↗
        </a>
      </div>
    </article>
  )
}
