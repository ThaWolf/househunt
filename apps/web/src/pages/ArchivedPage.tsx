import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { interestApi } from '@/api/endpoints'
import type { InterestItem } from '@/api/types'
import { AppScoreBadge } from '@/components/AppScoreBadge'
import { ListSelector } from '@/components/ListSelector'
import { LoadingState, ErrorState } from '@/components/LoadingState'
import { VisitDateCell } from '@/components/VisitDateCell'
import { useActiveList } from '@/context/ActiveListContext'
import { formatLocation, formatMoney, primaryImageUrl } from '@/lib/format'

function addedByLabel(item: InterestItem): string {
  const ab = item.addedBy
  if (!ab) return '—'
  return ab.displayName?.trim() || ab.email
}

export function ArchivedPage() {
  const { activeListId } = useActiveList()
  const [items, setItems] = useState<InterestItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!activeListId) return
    setLoading(true)
    setError(null)
    try {
      const res = await interestApi.list('archived', 50, 0, activeListId)
      setItems(res.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar archivadas')
    } finally {
      setLoading(false)
    }
  }, [activeListId])

  useEffect(() => {
    void load()
  }, [load])

  async function restore(item: InterestItem) {
    try {
      await interestApi.restore(item.id)
      setItems((prev) => prev.filter((i) => i.id !== item.id))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al restaurar')
    }
  }

  if (!activeListId || loading) return <LoadingState label="Cargando archivadas…" />
  if (error && !items.length) {
    return <ErrorState message={error} onRetry={() => void load()} />
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="font-display text-4xl font-bold text-ink">Archivadas</h1>
          <p className="text-sm text-ink-muted">
            Misma lista compartida — restaurá a interés activo.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ListSelector />
          <Link to="/interest" className="hh-btn-ghost no-underline text-sm">
            Volver a interés
          </Link>
        </div>
      </div>

      {error && (
        <p className="mb-3 text-sm text-danger" role="alert">
          {error}
        </p>
      )}

      {items.length === 0 ? (
        <p className="py-12 text-center text-ink-muted">No hay propiedades archivadas.</p>
      ) : (
        <div className="overflow-x-auto rounded border border-line bg-surface">
          <table className="w-full min-w-[820px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line bg-paper/80 text-[10px] uppercase tracking-wide text-ink-muted font-mono">
                <th className="px-2 py-2 w-12" />
                <th className="px-2 py-2">Título</th>
                <th className="px-2 py-2">Agregado por</th>
                <th className="px-2 py-2">Precio</th>
                <th className="px-2 py-2">Localidad</th>
                <th className="px-2 py-2">Rooms</th>
                <th className="px-2 py-2">App</th>
                <th className="px-2 py-2">User</th>
                <th className="px-2 py-2">Fecha visita</th>
                <th className="px-2 py-2">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const thumb = primaryImageUrl(item.property.images)
                return (
                  <tr key={item.id} className="border-b border-line/80 hover:bg-paper/60">
                    <td className="px-2 py-1.5">
                      <div className="h-9 w-9 overflow-hidden rounded bg-line/50 grayscale">
                        {thumb ? (
                          <img src={thumb} alt="" className="h-full w-full object-cover" />
                        ) : null}
                      </div>
                    </td>
                    <td className="px-2 py-1.5">
                      <Link
                        to={`/properties/${item.property.id}`}
                        className="font-medium text-ink no-underline hover:text-accent line-clamp-2"
                      >
                        {item.property.title}
                      </Link>
                    </td>
                    <td className="px-2 py-1.5 text-xs text-ink-muted truncate max-w-[120px]">
                      {addedByLabel(item)}
                    </td>
                    <td className="px-2 py-1.5 font-mono text-xs">
                      {formatMoney(item.property.price)}
                    </td>
                    <td className="px-2 py-1.5 text-xs text-ink-muted truncate max-w-[140px]">
                      {formatLocation(item.property.address)}
                    </td>
                    <td className="px-2 py-1.5 font-mono text-xs">
                      {item.rooms ?? item.property.rooms ?? '—'}
                    </td>
                    <td className="px-2 py-1.5">
                      <AppScoreBadge score={item.property.appScore} size="sm" />
                    </td>
                    <td className="px-2 py-1.5 font-mono text-xs">
                      {item.userScore ?? '—'}
                    </td>
                    <td className="px-2 py-1.5">
                      <VisitDateCell visit={item.visit} />
                    </td>
                    <td className="px-2 py-1.5">
                      <button
                        type="button"
                        className="hh-btn-accent text-xs py-1"
                        onClick={() => void restore(item)}
                      >
                        Restaurar
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
