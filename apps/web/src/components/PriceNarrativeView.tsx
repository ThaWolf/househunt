import type { PriceNarrative, PriceStance } from '@/api/types'
import { formatMoney } from '@/lib/format'

type Props = {
  narrative: PriceNarrative | null | undefined
}

const STANCE_LABEL: Record<PriceStance, string> = {
  low: 'Por debajo del cohort',
  fair: 'Alineado al cohort',
  high: 'Por encima del cohort',
  unknown: 'Sin cohort suficiente',
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
      <p className="text-sm leading-relaxed text-ink-muted mb-3">
        {narrative.summary}
      </p>
      <dl className="flex flex-wrap gap-x-4 gap-y-1 text-xs font-mono text-ink-muted">
        <div>
          <dt className="hh-label inline">Stance</dt>{' '}
          <dd className="inline text-ink">{STANCE_LABEL[narrative.stance]}</dd>
        </div>
        <div>
          <dt className="hh-label inline">Pares</dt>{' '}
          <dd className="inline text-ink">{narrative.peersSampleSize}</dd>
        </div>
        {median && (
          <div>
            <dt className="hh-label inline">Mediana peers</dt>{' '}
            <dd className="inline text-ink">{median}</dd>
          </div>
        )}
      </dl>
    </section>
  )
}
