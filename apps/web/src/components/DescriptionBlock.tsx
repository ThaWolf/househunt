import { useState } from 'react'

type Props = {
  description: string | null | undefined
  excerpt?: string | null
  collapseAt?: number
}

const DEFAULT_COLLAPSE = 420

export function DescriptionBlock({
  description,
  excerpt,
  collapseAt = DEFAULT_COLLAPSE,
}: Props) {
  const full = description?.trim() || null
  const teaser = excerpt?.trim() || null
  const text = full ?? teaser
  const [expanded, setExpanded] = useState(false)

  if (!text) return null

  const needsCollapse = text.length > collapseAt
  const shown =
    !needsCollapse || expanded ? text : `${text.slice(0, collapseAt).trimEnd()}…`

  return (
    <div>
      <h2 className="font-display text-xl font-semibold mb-2">Descripción</h2>
      <p className="text-sm text-ink-muted whitespace-pre-wrap leading-relaxed">
        {shown}
      </p>
      {needsCollapse && (
        <button
          type="button"
          className="mt-2 font-mono text-xs text-accent hover:underline"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
        >
          {expanded ? 'Ver menos' : 'Ver descripción completa'}
        </button>
      )}
      {!full && teaser && (
        <p className="mt-1 font-mono text-[10px] text-ink-muted">
          Solo excerpt — el aviso completo aún no llegó del portal.
        </p>
      )}
    </div>
  )
}
