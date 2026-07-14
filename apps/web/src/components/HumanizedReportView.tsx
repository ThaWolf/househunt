import type {
  HumanizedReport,
  RiskHit,
  ScoreComponent,
  ScoreComponentId,
} from '@/api/types'
import {
  SCORE_COMPONENT_COPY,
  normalizeScoreComponentId,
} from '@/api/types'
import { AppScoreBadge } from '@/components/AppScoreBadge'

type Props = {
  report: HumanizedReport | null
  fallbackAppScore?: number | null
}

function displayLabel(c: ScoreComponent): string {
  const id = normalizeScoreComponentId(c.id)
  const canonical = SCORE_COMPONENT_COPY[id]
  // Prefer BE label unless legacy "Riesgo" / raw risk id
  if (id === 'riskSafety') return canonical.label
  if (c.label?.trim()) return c.label
  return canonical.label
}

function displayHelp(c: ScoreComponent): string {
  if (c.helpText?.trim()) return c.helpText
  return SCORE_COMPONENT_COPY[normalizeScoreComponentId(c.id)].helpText
}

function evidenceLine(c: ScoreComponent): string | null {
  return c.summary?.trim() || c.note?.trim() || null
}

function hitKeyword(hit: RiskHit): string {
  return hit.keyword ?? hit.term ?? ''
}

function hitLabel(hit: RiskHit): string {
  return hit.label?.trim() || hitKeyword(hit) || 'Señal'
}

function riskSubtitle(
  component: ScoreComponent | undefined,
  riskHits: RiskHit[],
): string | null {
  if (!component) return null
  const id = normalizeScoreComponentId(component.id)
  if (id !== 'riskSafety') return null
  if (riskHits.length === 0 && component.score >= 80) {
    return 'Sin señales de riesgo en el aviso'
  }
  return null
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
            <ul className="mb-4 space-y-4" aria-label="Componentes del score">
              {report.components.map((c) => {
                const id = normalizeScoreComponentId(c.id)
                const label = displayLabel(c)
                const help = displayHelp(c)
                const evidence = evidenceLine(c)
                const riskHint = riskSubtitle(c, report.riskHits)

                return (
                  <li key={`${c.id}-${label}`}>
                    <div className="mb-0.5 flex items-baseline justify-between gap-2 text-sm">
                      <span className="font-medium text-ink">{label}</span>
                      <span className="font-mono text-xs text-ink-muted">
                        {Math.round(c.score)}
                        {c.maxScore ? ` / ${Math.round(c.maxScore)}` : ''}
                        <span className="ml-1 text-ink-muted/70">
                          ({Math.round(c.barPct)}%)
                        </span>
                      </span>
                    </div>
                    <p className="mb-1.5 text-xs leading-snug text-ink-muted">
                      {help}
                    </p>
                    <div
                      className="h-2 overflow-hidden rounded-full bg-paper"
                      role="progressbar"
                      aria-valuenow={Math.round(c.barPct)}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={label}
                    >
                      <div
                        className="h-full rounded-full bg-score transition-[width] duration-300"
                        style={{
                          width: `${Math.max(0, Math.min(100, c.barPct))}%`,
                        }}
                      />
                    </div>
                    {riskHint && (
                      <p className="mt-1 text-xs text-accent">{riskHint}</p>
                    )}
                    {evidence && (
                      <p className="mt-1 text-xs text-ink-muted">{evidence}</p>
                    )}
                    {id === 'riskSafety' && report.riskHits.length > 0 && (
                      <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-xs text-warn">
                        {report.riskHits.map((hit) => {
                          const kw = hitKeyword(hit)
                          const lb = hitLabel(hit)
                          return (
                            <li key={`${kw}-${lb}`}>
                              <span className="font-medium">{lb}</span>
                              {kw && kw !== lb && (
                                <span className="ml-1 font-mono text-[10px] text-ink-muted">
                                  (“{kw}”)
                                </span>
                              )}
                            </li>
                          )
                        })}
                      </ul>
                    )}
                  </li>
                )
              })}
            </ul>
          )}

          {/* Hits when riskSafety bar missing but hits exist */}
          {report.riskHits.length > 0 &&
            !report.components.some(
              (c) => normalizeScoreComponentId(c.id) === 'riskSafety',
            ) && (
              <div>
                <h3 className="hh-label mb-1">Salud legal / riesgo</h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-warn">
                  {report.riskHits.map((hit) => (
                    <li key={`${hitKeyword(hit)}-${hitLabel(hit)}`}>
                      {hitLabel(hit)}
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

/** Exported for tests — ensure UI never shows ambiguous “Riesgo” alone for riskSafety. */
export function scoreComponentDisplayId(
  id: ScoreComponentId,
): Exclude<ScoreComponentId, 'risk'> {
  return normalizeScoreComponentId(id)
}
