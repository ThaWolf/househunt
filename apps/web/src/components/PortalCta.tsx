import type { DataSource } from '@/api/types'
import { canOpenPortalCta } from '@/lib/listingFidelity'

type Props = {
  dataSource: DataSource
  sourceUrl: string
  /** Card uses short copy; detail uses longer. */
  variant?: 'card' | 'detail'
  className?: string
}

/**
 * E18 — portal CTA: hide/disable for demo_stub or invalid URL.
 * fixture_curated + valid URL → show.
 */
export function PortalCta({
  dataSource,
  sourceUrl,
  variant = 'card',
  className = '',
}: Props) {
  const open = canOpenPortalCta({ dataSource, sourceUrl })
  const label =
    variant === 'detail' ? 'Abrir publicación original ↗' : 'Ver en portal ↗'

  if (open) {
    return (
      <a
        href={sourceUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={
          className ||
          (variant === 'detail'
            ? 'hh-btn-ghost inline-flex no-underline text-sm'
            : 'font-mono text-[11px] text-accent no-underline hover:underline')
        }
      >
        {label}
      </a>
    )
  }

  if (dataSource === 'demo_stub') {
    return (
      <span
        className={
          className ||
          'font-mono text-[11px] text-ink-muted cursor-not-allowed'
        }
        title="Sin aviso real (demo)"
        aria-disabled="true"
        data-testid="portal-cta-disabled"
      >
        Sin aviso real (demo)
      </span>
    )
  }

  // fixture_curated / live with bad URL — no fake link
  return (
    <span
      className={
        className || 'font-mono text-[11px] text-ink-muted cursor-not-allowed'
      }
      title="URL de portal no disponible"
      aria-disabled="true"
      data-testid="portal-cta-disabled"
    >
      Portal no disponible
    </span>
  )
}
