import type { InterestFlags } from '@/api/types'
import { interestBadgeLabel } from '@/lib/format'

export function InterestBadge({ interest }: { interest?: InterestFlags | null }) {
  const label = interestBadgeLabel(interest)
  if (!label) return null

  const archived = label === 'archivada'
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
        archived
          ? 'bg-ink/10 text-ink-muted'
          : 'bg-accent-soft text-accent'
      }`}
    >
      {label === 'interés' ? 'en interés' : 'archivada'}
    </span>
  )
}
