import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { calendarApi, metaApi } from '@/api/endpoints'
import type { CalendarEvent } from '@/api/types'
import { LoadingState, ErrorState } from '@/components/LoadingState'
import { daysInMonthGrid, endOfMonth, startOfMonth } from '@/lib/format'

export function CalendarPage() {
  const [anchor, setAnchor] = useState(() => new Date())
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [googleCal, setGoogleCal] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)

  const cells = useMemo(() => daysInMonthGrid(anchor), [anchor])
  const monthLabel = anchor.toLocaleDateString('es-AR', {
    month: 'long',
    year: 'numeric',
  })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const from = startOfMonth(anchor).toISOString()
      const to = endOfMonth(anchor).toISOString()
      const [cal, meta] = await Promise.all([
        calendarApi.list(from, to),
        metaApi.adapters().catch(() => null),
      ])
      setEvents(cal.events)
      setGoogleCal(!!meta?.features?.googleCalendar)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar calendario')
    } finally {
      setLoading(false)
    }
  }, [anchor])

  useEffect(() => {
    void load()
  }, [load])

  const eventsByDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>()
    for (const ev of events) {
      if (!ev.visit?.at) continue
      const d = new Date(ev.visit.at)
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
      const list = map.get(key) ?? []
      list.push(ev)
      map.set(key, list)
    }
    return map
  }, [events])

  async function syncGoogle() {
    setSyncing(true)
    setSyncMsg(null)
    try {
      const res = await calendarApi.sync()
      setSyncMsg(`Sincronizados: ${res.synced} · fallidos: ${res.failed}`)
    } catch (err) {
      if (err instanceof ApiError && err.code === 'feature_disabled') {
        setGoogleCal(false)
        setSyncMsg('Sync Google Calendar deshabilitado en el servidor')
      } else {
        setSyncMsg(err instanceof ApiError ? err.message : 'Error de sync')
      }
    } finally {
      setSyncing(false)
    }
  }

  if (loading) return <LoadingState label="Cargando calendario…" />
  if (error && !events.length) {
    return <ErrorState message={error} onRetry={() => void load()} />
  }

  const today = new Date()

  return (
    <div className="animate-fade-in">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-4xl font-bold text-ink capitalize">
            {monthLabel}
          </h1>
          <p className="text-sm text-ink-muted">
            Visitas agendadas · click en evento → detalle
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="hh-btn-ghost text-sm"
            onClick={() =>
              setAnchor(new Date(anchor.getFullYear(), anchor.getMonth() - 1, 1))
            }
          >
            ← Mes
          </button>
          <button
            type="button"
            className="hh-btn-ghost text-sm"
            onClick={() => setAnchor(new Date())}
          >
            Hoy
          </button>
          <button
            type="button"
            className="hh-btn-ghost text-sm"
            onClick={() =>
              setAnchor(new Date(anchor.getFullYear(), anchor.getMonth() + 1, 1))
            }
          >
            Mes →
          </button>
          {googleCal && (
            <button
              type="button"
              className="hh-btn-accent text-sm"
              disabled={syncing}
              onClick={() => void syncGoogle()}
            >
              {syncing ? 'Sync…' : 'Sync Google Calendar'}
            </button>
          )}
        </div>
      </div>

      {syncMsg && (
        <p className="mb-3 font-mono text-xs text-ink-muted" role="status">
          {syncMsg}
        </p>
      )}
      {error && (
        <p className="mb-3 text-sm text-danger" role="alert">
          {error}
        </p>
      )}

      <div className="grid grid-cols-7 gap-px rounded-lg border border-line bg-line overflow-hidden">
        {['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'].map((d) => (
          <div
            key={d}
            className="bg-paper px-2 py-1.5 font-mono text-[10px] uppercase text-ink-muted"
          >
            {d}
          </div>
        ))}
        {cells.map((day) => {
          const inMonth = day.getMonth() === anchor.getMonth()
          const key = `${day.getFullYear()}-${day.getMonth()}-${day.getDate()}`
          const dayEvents = eventsByDay.get(key) ?? []
          const isToday =
            day.getDate() === today.getDate() &&
            day.getMonth() === today.getMonth() &&
            day.getFullYear() === today.getFullYear()

          return (
            <div
              key={key + String(inMonth)}
              className={`min-h-[88px] bg-surface p-1.5 ${
                inMonth ? '' : 'opacity-40'
              } ${isToday ? 'ring-1 ring-inset ring-accent' : ''}`}
            >
              <div className="font-mono text-[11px] text-ink-muted mb-1">
                {day.getDate()}
              </div>
              <ul className="space-y-1">
                {dayEvents.map((ev) => (
                  <li key={ev.interestId + ev.propertyId} className="animate-fade-in">
                    <Link
                      to={`/properties/${ev.propertyId}`}
                      className="block truncate rounded bg-accent-soft px-1 py-0.5 text-[10px] leading-tight text-accent no-underline hover:bg-accent hover:text-white transition-colors"
                      title={ev.title}
                    >
                      {ev.visit.at
                        ? new Date(ev.visit.at).toLocaleTimeString('es-AR', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })
                        : ''}{' '}
                      {ev.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}
