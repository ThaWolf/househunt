import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { interestApi, propertiesApi } from '@/api/endpoints'
import type { PropertyDetailResponse, Visit } from '@/api/types'
import { PORTAL_LABELS } from '@/api/types'
import { AppScoreBadge } from '@/components/AppScoreBadge'
import { HumanizedReportView } from '@/components/HumanizedReportView'
import { ImageGallery } from '@/components/ImageGallery'
import { InterestBadge } from '@/components/InterestBadge'
import { LoadingState, ErrorState } from '@/components/LoadingState'
import { UserScoreInput } from '@/components/UserScoreInput'
import { VisitControls } from '@/components/VisitControls'
import { formatLocation, formatMoney } from '@/lib/format'

export function DetailPage() {
  const { propertyId } = useParams<{ propertyId: string }>()
  const [data, setData] = useState<PropertyDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const [userScore, setUserScore] = useState<number | null>(null)
  const [comments, setComments] = useState('')
  const [visit, setVisit] = useState<Visit>({ status: 'none', at: null })
  const [interestId, setInterestId] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!propertyId) return
    setLoading(true)
    setError(null)
    try {
      const res = await propertiesApi.get(propertyId)
      setData(res)
      setUserScore(res.interest?.userScore ?? null)
      setComments(res.interest?.comments ?? '')
      setVisit(res.interest?.visit ?? { status: 'none', at: null })

      if (res.interest?.state) {
        const state = res.interest.state
        const list = await interestApi.list(state, 100, 0)
        const hit = list.items.find((i) => i.property.id === propertyId)
        setInterestId(hit?.id ?? null)
        if (hit) {
          setUserScore(hit.userScore)
          setComments(hit.comments ?? '')
          setVisit(hit.visit)
        }
      } else {
        setInterestId(null)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar detalle')
    } finally {
      setLoading(false)
    }
  }, [propertyId])

  useEffect(() => {
    void load()
  }, [load])

  async function addInterest() {
    if (!propertyId) return
    setBusy(true)
    setMsg(null)
    try {
      const item = await interestApi.create({ propertyId })
      setInterestId(item.id)
      setMsg('Agregada a interés')
      await load()
    } catch (err) {
      setMsg(
        err instanceof ApiError
          ? err.code === 'interest_exists'
            ? 'Ya está en interés o archivadas — restaurá desde Archivadas si hace falta.'
            : err.message
          : 'No se pudo agregar',
      )
    } finally {
      setBusy(false)
    }
  }

  async function saveUserFields(e?: FormEvent) {
    e?.preventDefault()
    if (!interestId || !propertyId || !data?.userFieldsEnabled) return
    setBusy(true)
    setMsg(null)
    try {
      await interestApi.patch(interestId, {
        userScore,
        comments: comments || null,
      })
      await propertiesApi.putVisit(propertyId, visit)
      setMsg('Guardado')
      await load()
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : 'Error al guardar')
    } finally {
      setBusy(false)
    }
  }

  async function archive() {
    if (!interestId) return
    setBusy(true)
    try {
      await interestApi.archive(interestId)
      await load()
      setMsg('Archivada')
    } catch (err) {
      setMsg(err instanceof ApiError ? err.message : 'Error al archivar')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <LoadingState label="Cargando propiedad…" />
  if (error || !data) {
    return (
      <ErrorState
        title="Detalle no disponible"
        message={error ?? undefined}
        onRetry={() => void load()}
      />
    )
  }

  const { property, report, userFieldsEnabled, interest } = data
  const canAdd =
    !interest?.state || (interest.state !== 'active' && interest.state !== 'archived')

  return (
    <div className="animate-fade-in">
      <div className="mb-3 flex flex-wrap gap-2 text-sm">
        <Link to="/results" className="text-ink-muted no-underline hover:text-accent">
          ← Resultados
        </Link>
        <span className="text-line">/</span>
        <Link to="/interest" className="text-ink-muted no-underline hover:text-accent">
          Interés
        </Link>
      </div>

      <ImageGallery images={property.images ?? []} alt={property.title} />

      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-2 flex flex-wrap gap-2">
            <InterestBadge interest={interest} />
            <span className="rounded bg-ink/5 px-1.5 py-0.5 font-mono text-[10px] uppercase text-ink-muted">
              {PORTAL_LABELS[property.portal]}
            </span>
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold text-ink leading-tight">
            {property.title}
          </h1>
          <p className="mt-1 font-mono text-accent text-lg">
            {formatMoney(property.price)}
          </p>
          <p className="mt-1 text-sm text-ink-muted">
            {formatLocation(property.address)}
          </p>
        </div>
        <AppScoreBadge score={property.appScore} size="lg" />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <section className="space-y-4">
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <dt className="hh-label">Habitaciones</dt>
              <dd className="font-mono">{property.rooms ?? '—'}</dd>
            </div>
            <div>
              <dt className="hh-label">Baños</dt>
              <dd className="font-mono">{property.bathrooms ?? '—'}</dd>
            </div>
            <div>
              <dt className="hh-label">Cubiertos</dt>
              <dd className="font-mono">
                {property.area?.coveredM2 != null
                  ? `${property.area.coveredM2} m²`
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="hh-label">Total</dt>
              <dd className="font-mono">
                {property.area?.totalM2 != null
                  ? `${property.area.totalM2} m²`
                  : '—'}
              </dd>
            </div>
          </dl>

          {property.amenities && property.amenities.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {property.amenities.map((a) => (
                <span
                  key={a}
                  className="rounded bg-accent-soft px-2 py-0.5 font-mono text-[11px] text-accent"
                >
                  {a}
                </span>
              ))}
            </div>
          )}

          {property.description && (
            <div>
              <h2 className="font-display text-xl font-semibold mb-2">Descripción</h2>
              <p className="text-sm text-ink-muted whitespace-pre-wrap leading-relaxed">
                {property.description}
              </p>
            </div>
          )}

          <HumanizedReportView
            report={report}
            fallbackAppScore={property.appScore}
          />

          <a
            href={property.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="hh-btn-ghost inline-flex no-underline text-sm"
          >
            Abrir publicación original ↗
          </a>
        </section>

        <aside className="space-y-4">
          {canAdd && (
            <div className="rounded-lg border border-line bg-surface p-4">
              <p className="text-sm text-ink-muted mb-3">
                Agregá a interés para score personal, visitas y comentarios.
              </p>
              <button
                type="button"
                className="hh-btn-accent w-full"
                disabled={busy}
                onClick={() => void addInterest()}
              >
                Agregar a interés
              </button>
            </div>
          )}

          {userFieldsEnabled ? (
            <form
              onSubmit={(e) => void saveUserFields(e)}
              className="rounded-lg border border-accent/30 bg-accent-soft/40 p-4 space-y-4"
            >
              <h2 className="font-display text-xl font-semibold">Tu seguimiento</h2>
              <div>
                <label className="hh-label">UserScore (1–10)</label>
                <UserScoreInput
                  id="detail-userscore"
                  value={userScore}
                  onChange={setUserScore}
                  disabled={busy}
                />
              </div>
              <VisitControls visit={visit} onChange={setVisit} disabled={busy} />
              <div>
                <label className="hh-label" htmlFor="comments">
                  Comentarios
                </label>
                <textarea
                  id="comments"
                  className="hh-input min-h-[80px]"
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  disabled={busy}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <button type="submit" className="hh-btn-primary" disabled={busy}>
                  Guardar
                </button>
                {interest?.state === 'active' && (
                  <button
                    type="button"
                    className="hh-btn-ghost"
                    disabled={busy}
                    onClick={() => void archive()}
                  >
                    Archivar
                  </button>
                )}
              </div>
            </form>
          ) : (
            <div className="rounded-lg border border-dashed border-line p-4 text-sm text-ink-muted">
              UserScore, visita y comentarios aparecen solo si la propiedad está en
              interés o archivadas.
            </div>
          )}

          {msg && (
            <p className="text-sm font-mono text-ink-muted" role="status">
              {msg}
            </p>
          )}
        </aside>
      </div>
    </div>
  )
}
