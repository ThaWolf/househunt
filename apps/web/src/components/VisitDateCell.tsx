import type { Visit, VisitStatus } from '@/api/types'
import { formatVisitDateTime } from '@/lib/format'

type Props = {
  visit: Visit
  className?: string
}

export function VisitDateCell({ visit, className = '' }: Props) {
  const status = (visit?.status ?? 'none') as VisitStatus
  const text = formatVisitDateTime(visit?.at ?? null, status)
  if (!text) {
    return <span className={`text-ink-muted ${className}`}>—</span>
  }
  return <span className={`font-mono text-xs whitespace-nowrap ${className}`}>{text}</span>
}
