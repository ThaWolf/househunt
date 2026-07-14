type Props = {
  value: number | null | undefined
  onChange: (value: number | null) => void
  disabled?: boolean
  id?: string
}

/** Numeric UserScore 1–10 — not stars. */
export function UserScoreInput({ value, onChange, disabled, id }: Props) {
  return (
    <div className="inline-flex items-center gap-1.5">
      <label htmlFor={id} className="sr-only">
        UserScore 1 a 10
      </label>
      <input
        id={id}
        type="number"
        min={1}
        max={10}
        step={1}
        disabled={disabled}
        value={value ?? ''}
        placeholder="—"
        className="hh-input w-16 text-center font-mono tabular-nums py-1"
        onChange={(e) => {
          const raw = e.target.value
          if (raw === '') {
            onChange(null)
            return
          }
          const n = Number(raw)
          if (Number.isNaN(n)) return
          const clamped = Math.min(10, Math.max(1, Math.round(n)))
          onChange(clamped)
        }}
        aria-label="UserScore del 1 al 10"
      />
      <span className="text-[10px] font-mono text-ink-muted">/10</span>
    </div>
  )
}
