import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { interestApi, propertiesApi } from '@/api/endpoints'
import type { PropertyDetailResponse, Visit } from '@/api/types'
import { PORTAL_LABELS } from '@/api/types'
import { AppScoreBadge } from '@/components/AppScoreBadge'
import { InterestBadge } from '@/components/InterestBadge'
import { LoadingState, ErrorState } from '@/components/LoadingState'
import { UserScoreInput } from '@/components/UserScoreInput'
import { VisitControls } from '@/components/VisitControls'
import { formatLocation, formatMoney, primaryImageUrl } from '@/lib/format'

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

      // Resolve interest id when in list (need for patch/archive)
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
  const hero = primaryImageUrl(property.images)
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

      {/* Full-bleed-ish gallery */}
      <div className="relative -mx-4 sm:mx-0 mb-6 overflow-hidden sm:rounded-lg bg-ink min-h-[240px] max-h-[420px]">
        {hero ? (
          <img
            src={hero}
            alt=""
            className="h-[280px] sm:h-[400px] w-full object-cover opacity-95"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
            }}
          />
        ) : (
          <div className="flex h-[280px] items-center justify-center text-white/40 font-mono text-sm">
            Sin imagen
          </div>
        )}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-ink/90 to-transparent p-4 sm:p-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <div className="mb-2 flex flex-wrap gap-2">
                <InterestBadge interest={interest} />
                <span className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[10px] uppercase text-white/80">
                  {PORTAL_LABELS[property.portal]}
                </span>
              </div>
              <h1 className="font-display text-3xl sm:text-4xl font-bold text-white leading-tight">
                {property.title}
              </h1>
              <p className="mt-1 font-mono text-teal-300 text-lg">
                {formatMoney(property.price)}
              </p>
            </div>
            <AppScoreBadge score={property.appScore} size="lg" />
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <section className="space-y-4">
          <p className="text-sm text-ink-muted">{formatLocation(property.address)}</p>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <dt className="hh-label">Ambientes</dt>
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

          {property.description && (
            <div>
              <h2 className="font-display text-xl font-semibold mb-2">Descripción</h2>
              <p className="text-sm text-ink-muted whitespace-pre-wrap leading-relaxed">
                {property.description}
              </p>
            </div>
          )}

          <div className="rounded-lg border border-line bg-surface p-4">
            <h2 className="font-display text-xl font-semibold mb-2">
              Reporte Househunt
            </h2>
            {report ? (
              <>
                <p className="text-sm mb-2">{report.summary ?? 'Sin resumen.'}</p>
                {report.riskHits?.length > 0 && (
                  <ul className="list-disc pl-5 text-sm text-warn">
                    {report.riskHits.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                )}
                <p className="mt-2 font-mono text-[10px] text-ink-muted">
                  {report.generatedAt}
                </p>
              </>
            ) : (
              <p className="text-sm text-ink-muted">Reporte aún no generado.</p>
            )}
            {property.scoreBreakdown && (
              <pre className="mt-3 overflow-auto rounded bg-paper p-2 font-mono text-[10px] text-ink-muted">
                {JSON.stringify(property.scoreBreakdown, null, 2)}
              </pre>
            )}
          </div>

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
