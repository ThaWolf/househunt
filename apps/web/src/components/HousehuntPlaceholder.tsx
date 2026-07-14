type Props = {
  className?: string
  label?: string
  /** compact = card thumb; hero = gallery */
  size?: 'compact' | 'hero'
}

/** Househunt-owned placeholder — never stock CDN (E19). */
export function HousehuntPlaceholder({
  className = '',
  label = 'Sin foto del aviso',
  size = 'hero',
}: Props) {
  const tall = size === 'hero'
  return (
    <div
      className={`hh-placeholder flex flex-col items-center justify-center gap-2 text-center ${
        tall ? 'h-[280px] sm:h-[400px]' : 'h-full min-h-[8rem]'
      } ${className}`}
      role="img"
      aria-label={label}
      data-testid="househunt-placeholder"
    >
      <span
        className={`font-display font-bold tracking-wide text-white/90 ${
          tall ? 'text-3xl sm:text-4xl' : 'text-lg'
        }`}
      >
        Househunt
      </span>
      {label ? (
        <span
          className={`font-mono text-white/55 ${tall ? 'text-xs' : 'text-[10px]'}`}
        >
          {label}
        </span>
      ) : null}
    </div>
  )
}
