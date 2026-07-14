import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { interestApi, propertiesApi } from '@/api/endpoints'
import type { AmenityHighlight, InterestItem } from '@/api/types'
import { AppScoreBadge } from '@/components/AppScoreBadge'
import { DataSourceBadge } from '@/components/DataSourceBadge'
import { HousehuntPlaceholder } from '@/components/HousehuntPlaceholder'
import { LoadingState, ErrorState } from '@/components/LoadingState'
import { UserScoreInput } from '@/components/UserScoreInput'
import { formatLocation, formatMoney, primaryImageUrl } from '@/lib/format'
import { resolveDataSource } from '@/lib/listingFidelity'

function AmenityCell({ items }: { items: AmenityHighlight[] }) {
  if (!items?.length) {
    return <span className="text-ink-muted">—</span>
  }
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((a) => (
        <span
          key={a.token}
          title={a.label}
          className={`inline-flex items-center rounded px-1 py-0.5 font-mono text-[10px] ${
            a.present
              ? 'bg-accent-soft text-accent'
              : 'bg-paper text-ink-muted/60 line-through decoration-ink-muted/30'
          }`}
        >
          {a.present ? '✓' : '—'} {a.label}
        </span>
      ))}
    </div>
  )
}

export function InterestPage() {
  const [items, setItems] = useState<InterestItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [flashId, setFlashId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await interestApi.list('active')
      setItems(res.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar interés')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function patchScore(item: InterestItem, userScore: number | null) {
    try {
      await interestApi.patch(item.id, { userScore })
      setFlashId(item.id)
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, userScore } : i)),
      )
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al guardar score')
    }
  }

  async function archive(item: InterestItem) {
    try {
      await interestApi.archive(item.id)
      setItems((prev) => prev.filter((i) => i.id !== item.id))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al archivar')
    }
  }

  async function markVisit(item: InterestItem, status: 'scheduled' | 'visited' | 'none') {
    try {
      const visit =
        status === 'none'
          ? { status: 'none' as const, at: null }
          : {
              status,
              at: item.visit?.at ?? new Date().toISOString(),
            }
      await propertiesApi.putVisit(item.property.id, visit)
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, visit } : i)),
      )
      setFlashId(item.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al actualizar visita')
    }
  }

  if (loading) return <LoadingState label="Cargando interés…" />
  if (error && !items.length) {
    return <ErrorState message={error} onRetry={() => void load()} />
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="font-display text-4xl font-bold text-ink">Interés</h1>
          <p className="text-sm text-ink-muted">
            Tabla densa — rooms, amenities (pileta/jardín), UserScore, visita.
          </p>
        </div>
        <Link to="/archived" className="hh-btn-ghost no-underline text-sm">
          Ver archivadas
        </Link>
      </div>

      {error && (
        <p className="mb-3 text-sm text-danger" role="alert">
          {error}
        </p>
      )}

      {items.length === 0 ? (
        <p className="py-12 text-center text-ink-muted">
          Todavía no hay propiedades en interés.{' '}
          <Link to="/search">Buscar</Link>
        </p>
      ) : (
        <div className="overflow-x-auto rounded border border-line bg-surface">
          <table className="w-full min-w-[1020px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line bg-paper/80 text-[10px] uppercase tracking-wide text-ink-muted font-mono">
                <th className="px-2 py-2 font-medium w-12" />
                <th className="px-2 py-2 font-medium">Título</th>
                <th className="px-2 py-2 font-medium">Precio</th>
                <th className="px-2 py-2 font-medium">Localidad</th>
                <th className="px-2 py-2 font-medium">Rooms</th>
                <th className="px-2 py-2 font-medium">Amenities</th>
                <th className="px-2 py-2 font-medium">App</th>
                <th className="px-2 py-2 font-medium">User</th>
                <th className="px-2 py-2 font-medium">Visita</th>
                <th className="px-2 py-2 font-medium">💬</th>
                <th className="px-2 py-2 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const thumb = primaryImageUrl(item.property.images)
                const rooms = item.rooms ?? item.property.rooms
                const dataSource = resolveDataSource(item.property)
                return (
                  <tr
                    key={item.id}
                    className={`border-b border-line/80 hover:bg-accent-soft/30 ${
                      flashId === item.id ? 'animate-row-flash' : ''
                    }`}
                  >
                    <td className="px-2 py-1.5">
                      <div className="h-9 w-9 overflow-hidden rounded bg-line/50">
                        {thumb ? (
                          <img src={thumb} alt="" className="h-full w-full object-cover" />
                        ) : (
                          <HousehuntPlaceholder
                            size="compact"
                            label=""
                            className="!min-h-0 h-9"
                          />
                        )}
                      </div>
                    </td>
                    <td className="px-2 py-1.5 max-w-[220px]">
                      <div className="mb-0.5">
                        <DataSourceBadge dataSource={dataSource} />
                      </div>
                      <Link
                        to={`/properties/${item.property.id}`}
                        className="line-clamp-2 font-medium text-ink no-underline hover:text-accent"
                      >
                        {item.property.title}
                      </Link>
                    </td>
                    <td className="px-2 py-1.5 font-mono text-xs whitespace-nowrap">
                      {formatMoney(item.property.price)}
                    </td>
                    <td className="px-2 py-1.5 text-xs text-ink-muted max-w-[140px] truncate">
                      {formatLocation(item.property.address)}
                    </td>
                    <td className="px-2 py-1.5 font-mono text-xs">
                      {rooms ?? '—'}
                    </td>
                    <td className="px-2 py-1.5 max-w-[200px]">
                      <AmenityCell items={item.amenitiesHighlight ?? []} />
                    </td>
                    <td className="px-2 py-1.5">
                      <AppScoreBadge score={item.property.appScore} size="sm" />
                    </td>
                    <td className="px-2 py-1.5">
                      <UserScoreInput
                        id={`us-${item.id}`}
                        value={item.userScore}
                        onChange={(v) => void patchScore(item, v)}
                      />
                    </td>
                    <td className="px-2 py-1.5">
                      <select
                        className="hh-input py-1 text-xs w-[110px]"
                        value={item.visit?.status ?? 'none'}
                        onChange={(e) =>
                          void markVisit(
                            item,
                            e.target.value as 'scheduled' | 'visited' | 'none',
                          )
                        }
                      >
                        <option value="none">none</option>
                        <option value="scheduled">scheduled</option>
                        <option value="visited">visited</option>
                      </select>
                    </td>
                    <td className="px-2 py-1.5 text-center font-mono text-xs">
                      {item.commentFlag ? '●' : '·'}
                    </td>
                    <td className="px-2 py-1.5 whitespace-nowrap">
                      <button
                        type="button"
                        className="text-xs text-ink-muted hover:text-danger"
                        onClick={() => void archive(item)}
                      >
                        Archivar
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
