import type { Visit, VisitStatus } from '@/api/types'
import { fromLocalInputValue, toLocalInputValue } from '@/lib/format'

type Props = {
  visit: Visit | null | undefined
  onChange: (visit: Visit) => void
  disabled?: boolean
}

export function VisitControls({ visit, onChange, disabled }: Props) {
  const status: VisitStatus = visit?.status ?? 'none'
  const atLocal = toLocalInputValue(visit?.at)

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div>
        <label className="hh-label">Visita</label>
        <select
          className="hh-input py-1.5"
          disabled={disabled}
          value={status}
          onChange={(e) => {
            const next = e.target.value as VisitStatus
            if (next === 'none') {
              onChange({ status: 'none', at: null })
              return
            }
            onChange({
              status: next,
              at: visit?.at ?? new Date().toISOString(),
            })
          }}
        >
          <option value="none">Ninguna</option>
          <option value="scheduled">Agendada</option>
          <option value="visited">Visitada</option>
        </select>
      </div>
      {(status === 'scheduled' || status === 'visited') && (
        <div>
          <label className="hh-label">Fecha / hora</label>
          <input
            type="datetime-local"
            className="hh-input py-1.5"
            disabled={disabled}
            value={atLocal}
            onChange={(e) => {
              const v = e.target.value
              onChange({
                status,
                at: v ? fromLocalInputValue(v) : null,
              })
            }}
          />
        </div>
      )}
    </div>
  )
}
