import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { interestApi, propertiesApi } from '@/api/endpoints'
import type { InterestItem } from '@/api/types'
import { AddExternalListingModal } from '@/components/AddExternalListingModal'
import { AMENITY_LEGEND, AmenityCell } from '@/components/AmenityCell'
import { AppScoreBadge } from '@/components/AppScoreBadge'
import { DataSourceBadge } from '@/components/DataSourceBadge'
import { HousehuntPlaceholder } from '@/components/HousehuntPlaceholder'
import { InviteCollaboratorsModal } from '@/components/InviteCollaboratorsModal'
import { ListSelector } from '@/components/ListSelector'
import { LoadingState, ErrorState } from '@/components/LoadingState'
import { UserScoreInput } from '@/components/UserScoreInput'
import { VisitDateCell } from '@/components/VisitDateCell'
import { useActiveList } from '@/context/ActiveListContext'
import { formatLocation, formatMoney, primaryImageUrl } from '@/lib/format'
import { resolveDataSource } from '@/lib/listingFidelity'

function addedByLabel(item: InterestItem): string {
  const ab = item.addedBy
  if (!ab) return '—'
  return ab.displayName?.trim() || ab.email
}

export function InterestPage() {
  const { activeListId, activeList } = useActiveList()
  const [items, setItems] = useState<InterestItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [flashId, setFlashId] = useState<string | null>(null)
  const [showAddExternal, setShowAddExternal] = useState(false)
  const [showInvite, setShowInvite] = useState(false)

  const load = useCallback(async () => {
    if (!activeListId) return
    setLoading(true)
    setError(null)
    try {
      const res = await interestApi.list('active', 50, 0, activeListId)
      setItems(res.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar interés')
    } finally {
      setLoading(false)
    }
  }, [activeListId])

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

  function onExternalAdded(item: InterestItem) {
    setItems((prev) => [item, ...prev.filter((i) => i.id !== item.id)])
    setFlashId(item.id)
    setError(null)
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
    if (!activeListId) return
    try {
      const visit =
        status === 'none'
          ? { status: 'none' as const, at: null }
          : {
              status,
              at: item.visit?.at ?? new Date().toISOString(),
            }
      await propertiesApi.putVisit(item.property.id, visit, activeListId)
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, visit } : i)),
      )
      setFlashId(item.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al actualizar visita')
    }
  }

  if (!activeListId || loading) return <LoadingState label="Cargando interés…" />
  if (error && !items.length) {
    return <ErrorState message={error} onRetry={() => void load()} />
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="font-display text-4xl font-bold text-ink">Interés</h1>
          <p className="text-sm text-ink-muted">
            Lista compartida — rooms, amenities, UserScore, visita.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ListSelector />
          {activeList?.role === 'owner' && (
            <button
              type="button"
              className="hh-btn-ghost text-sm"
              onClick={() => setShowInvite(true)}
            >
              Invitar
            </button>
          )}
          <button
            type="button"
            className="hh-btn-accent text-sm"
            onClick={() => setShowAddExternal(true)}
          >
            + Agregar publicación externa
          </button>
          <Link to="/archived" className="hh-btn-ghost no-underline text-sm">
            Ver archivadas
          </Link>
        </div>
      </div>

      {error && (
        <p className="mb-3 text-sm text-danger" role="alert">
          {error}
        </p>
      )}

      {items.length === 0 ? (
        <p className="py-12 text-center text-ink-muted">
          Todavía no hay propiedades en interés.{' '}
          <Link to="/search">Buscar</Link> o agregá una{' '}
          <button
            type="button"
            className="text-accent underline"
            onClick={() => setShowAddExternal(true)}
          >
            publicación externa
          </button>
          .
        </p>
      ) : (
        <div className="overflow-x-auto rounded border border-line bg-surface">
          <table className="w-full min-w-[1120px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line bg-paper/80 text-[10px] uppercase tracking-wide text-ink-muted font-mono">
                <th className="px-2 py-2 font-medium w-12" />
                <th className="px-2 py-2 font-medium">Título</th>
                <th className="px-2 py-2 font-medium">Agregado por</th>
                <th className="px-2 py-2 font-medium">Precio</th>
                <th className="px-2 py-2 font-medium">Localidad</th>
                <th className="px-2 py-2 font-medium">Hab.</th>
                <th className="px-2 py-2 font-medium">
                  <span className="block">Amenities</span>
                  <span className="mt-0.5 block normal-case tracking-normal font-sans text-[9px] text-ink-muted/80">
                    {AMENITY_LEGEND}
                  </span>
                </th>
                <th
                  className="px-2 py-2 font-medium"
                  title="Estimación automática; con datos incompletos muchos avisos puntúan parecido."
                >
                  App
                </th>
                <th className="px-2 py-2 font-medium">User</th>
                <th className="px-2 py-2 font-medium">Visita</th>
                <th className="px-2 py-2 font-medium">Fecha visita</th>
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
                    <td className="px-2 py-1.5 max-w-[200px]">
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
                    <td className="px-2 py-1.5 text-xs text-ink-muted max-w-[120px] truncate">
                      {addedByLabel(item)}
                    </td>
                    <td className="px-2 py-1.5 font-mono text-xs whitespace-nowrap">
                      {formatMoney(item.property.price)}
                    </td>
                    <td className="px-2 py-1.5 text-xs text-ink-muted max-w-[120px] truncate">
                      {formatLocation(item.property.address)}
                    </td>
                    <td className="px-2 py-1.5 font-mono text-xs">
                      {rooms ?? '—'}
                    </td>
                    <td className="px-2 py-1.5 max-w-[180px]">
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
                        className="hh-input py-1 text-xs w-[100px]"
                        value={item.visit?.status ?? 'none'}
                        onChange={(e) =>
                          void markVisit(
                            item,
                            e.target.value as 'scheduled' | 'visited' | 'none',
                          )
                        }
                      >
                        <option value="none">Sin visita</option>
                        <option value="scheduled">Agendada</option>
                        <option value="visited">Visitada</option>
                      </select>
                    </td>
                    <td className="px-2 py-1.5">
                      <VisitDateCell visit={item.visit} />
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

      {showAddExternal && (
        <AddExternalListingModal
          onClose={() => setShowAddExternal(false)}
          onAdded={onExternalAdded}
        />
      )}
      {showInvite && (
        <InviteCollaboratorsModal onClose={() => setShowInvite(false)} />
      )}
    </div>
  )
}
