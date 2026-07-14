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
