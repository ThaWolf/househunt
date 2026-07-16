import { useId, useState } from 'react'

type Props = {
  /** Texto explicativo (amigable) que se muestra en hover/focus. */
  text: string
  /** Etiqueta accesible del score al que acompaña. */
  label?: string
}

/**
 * Botón "?" accesible que muestra una descripción breve en hover/focus.
 * Mantiene el detalle fuera del cuerpo del informe (menos ruido visual).
 */
export function InfoTooltip({ text, label }: Props) {
  const [open, setOpen] = useState(false)
  const id = useId()

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-label={label ? `Qué mide ${label}` : 'Más información'}
        aria-describedby={open ? id : undefined}
        title={text}
        className="flex h-4 w-4 items-center justify-center rounded-full border border-line text-[10px] font-semibold leading-none text-ink-muted transition-colors hover:bg-paper hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-score"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => {
          e.preventDefault()
          setOpen((v) => !v)
        }}
      >
        ?
      </button>
      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute left-1/2 top-6 z-20 w-56 -translate-x-1/2 rounded-md border border-line bg-surface p-2 text-xs font-normal leading-snug text-ink-muted shadow-lg"
        >
          {text}
        </span>
      )}
    </span>
  )
}
