export const APP_SCORE_TOOLTIP =
  'Estimación automática; con datos incompletos muchos avisos puntúan parecido.'

type Props = {
  score: number | null | undefined
  size?: 'sm' | 'md' | 'lg'
}

export function AppScoreBadge({ score, size = 'md' }: Props) {
  if (score == null) {
    return (
      <span className="font-mono text-xs text-ink-muted" title="AppScore pendiente">
        —
      </span>
    )
  }

  const sizeCls =
    size === 'lg'
      ? 'text-2xl px-3 py-1'
      : size === 'sm'
        ? 'text-xs px-1.5 py-0.5'
        : 'text-sm px-2 py-0.5'

  const tone =
    score >= 70
      ? 'bg-accent-soft text-accent'
      : score >= 40
        ? 'bg-amber-100 text-warn'
        : 'bg-red-50 text-danger'

  return (
    <span
      className={`inline-flex items-baseline gap-1 rounded font-mono font-medium tabular-nums ${sizeCls} ${tone}`}
      title={APP_SCORE_TOOLTIP}
    >
      <span className="text-[10px] uppercase opacity-70">App</span>
      {score}
    </span>
  )
}
