import { useEffect, useState } from 'react'

export function LoadingState({ label = 'Cargando…' }: { label?: string }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-16 text-ink-muted animate-fade-in"
      role="status"
      aria-live="polite"
    >
      <div className="h-8 w-8 rounded-full border-2 border-line border-t-accent animate-spin" />
      <p className="text-sm">{label}</p>
    </div>
  )
}

/** Long multi-portal scrap: spinner + elapsed timer + card skeleton grid. */
export function SearchLoadingProgress({
  label = 'Buscando en portales… esto puede tardar',
}: {
  label?: string
}) {
  const [elapsedSec, setElapsedSec] = useState(0)

  useEffect(() => {
    const t0 = Date.now()
    const id = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - t0) / 1000))
    }, 250)
    return () => window.clearInterval(id)
  }, [])

  const phase =
    elapsedSec < 4
      ? 'Consultando ZonaProp y Mercado Libre…'
      : elapsedSec < 10
        ? 'Ampliando a Argenprop, Remax y Century 21…'
        : 'Filtrando resultados y armando la respuesta…'

  return (
    <div
      className="animate-fade-in"
      role="status"
      aria-live="polite"
      aria-busy="true"
      data-testid="search-loading"
    >
      <div className="mb-6 flex flex-col items-center gap-2 text-center">
        <div className="h-8 w-8 rounded-full border-2 border-line border-t-accent animate-spin" />
        <p className="text-sm text-ink font-medium">{label}</p>
        <p className="text-xs text-ink-muted">{phase}</p>
        <p className="font-mono text-xs text-ink-muted" data-testid="search-elapsed">
          {elapsedSec}s
        </p>
        <div
          className="mt-1 h-1.5 w-48 max-w-full overflow-hidden rounded-full bg-line"
          aria-hidden
        >
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-300 ease-out"
            style={{
              width: `${Math.min(92, 12 + elapsedSec * 6)}%`,
            }}
          />
        </div>
      </div>

      <div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        data-testid="search-skeleton"
        aria-hidden
      >
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="hh-card overflow-hidden border border-line bg-surface"
          >
            <div className="aspect-[4/3] bg-line/60 animate-pulse" />
            <div className="space-y-2 p-3">
              <div className="h-3 w-[75%] rounded bg-line animate-pulse" />
              <div className="h-3 w-1/2 rounded bg-line/80 animate-pulse" />
              <div className="h-3 w-1/3 rounded bg-line/70 animate-pulse" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function ErrorState({
  title = 'Algo falló',
  message,
  onRetry,
}: {
  title?: string
  message?: string
  onRetry?: () => void
}) {
  return (
    <div
      className="rounded-lg border border-danger/30 bg-danger/5 px-4 py-6 text-center animate-fade-in"
      role="alert"
    >
      <h2 className="font-display text-xl text-danger mb-1">{title}</h2>
      {message && <p className="text-sm text-ink-muted mb-4">{message}</p>}
      {onRetry && (
        <button type="button" className="hh-btn-ghost" onClick={onRetry}>
          Reintentar
        </button>
      )}
    </div>
  )
}
