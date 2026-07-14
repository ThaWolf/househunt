import type { HumanizedReport } from '@/api/types'
import { AppScoreBadge } from '@/components/AppScoreBadge'

type Props = {
  report: HumanizedReport | null
  fallbackAppScore?: number | null
}

export function HumanizedReportView({ report, fallbackAppScore }: Props) {
  const score = report?.appScore ?? fallbackAppScore ?? null

  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-xl font-semibold">
          Reporte Househunt
        </h2>
        <AppScoreBadge score={score} size="md" />
      </div>

      {!report ? (
        <p className="text-sm text-ink-muted">Reporte aún no generado.</p>
      ) : (
        <>
          {report.summary ? (
            <p className="mb-4 text-sm leading-relaxed text-ink-muted">
              {report.summary}
            </p>
          ) : (
            <p className="mb-4 text-sm text-ink-muted">Sin resumen.</p>
          )}

          {report.components.length > 0 && (
            <ul className="mb-4 space-y-3" aria-label="Componentes del score">
              {report.components.map((c) => (
                <li key={c.id}>
                  <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
                    <span className="font-medium text-ink">{c.label}</span>
                    <span className="font-mono text-xs text-ink-muted">
                      {Math.round(c.score)}
                      {c.maxScore ? ` / ${Math.round(c.maxScore)}` : ''}
                      <span className="ml-1 text-ink-muted/70">
                        ({Math.round(c.barPct)}%)
                      </span>
                    </span>
                  </div>
                  <div
                    className="h-2 overflow-hidden rounded-full bg-paper"
                    role="progressbar"
                    aria-valuenow={Math.round(c.barPct)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label={c.label}
                  >
                    <div
                      className="h-full rounded-full bg-score transition-[width] duration-300"
                      style={{
                        width: `${Math.max(0, Math.min(100, c.barPct))}%`,
                      }}
                    />
                  </div>
                  {c.note && (
                    <p className="mt-1 font-mono text-[10px] text-ink-muted">
                      {c.note}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}

          {report.riskHits.length > 0 && (
            <div>
              <h3 className="hh-label mb-1">Riesgos detectados</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm text-warn">
                {report.riskHits.map((hit) => (
                  <li key={`${hit.term}-${hit.label}`}>
                    <span className="font-medium">{hit.label}</span>
                    {hit.term && hit.term !== hit.label && (
                      <span className="ml-1 font-mono text-[10px] text-ink-muted">
                        (“{hit.term}”)
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="mt-3 font-mono text-[10px] text-ink-muted">
            {report.generatedAt}
          </p>
        </>
      )}
    </div>
  )
}
