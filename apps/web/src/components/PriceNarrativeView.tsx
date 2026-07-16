import type { PriceNarrative } from '@/api/types'
import { formatMoney } from '@/lib/format'

type Props = {
  narrative: PriceNarrative | null | undefined
}

export function PriceNarrativeView({ narrative }: Props) {
  if (!narrative) return null

  const median =
    narrative.peerMedianAmount != null
      ? formatMoney({
          amount: narrative.peerMedianAmount,
          currency: narrative.currency ?? 'USD',
          period: null,
        })
      : null

  return (
    <section
      className="rounded-lg border border-line bg-surface p-4 animate-fade-in"
      aria-label="Comparativa de precio"
    >
      <h2 className="font-display text-xl font-semibold mb-2">
        Precio vs similares
      </h2>
      <p className="text-sm leading-relaxed text-ink-muted">
        {narrative.summary}
      </p>
      {median && narrative.peersSampleSize >= 3 && (
        <p className="mt-2 text-xs text-ink-muted">
          Precio típico de casas parecidas en la zona:{' '}
          <span className="font-medium text-ink">{median}</span>{' '}
          (sobre {narrative.peersSampleSize} avisos parecidos).
        </p>
      )}
    </section>
  )
}
