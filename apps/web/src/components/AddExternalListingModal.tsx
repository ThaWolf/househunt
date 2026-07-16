import { useState } from 'react'
import { ApiError } from '@/api/client'
import { interestApi } from '@/api/endpoints'
import type { InterestItem } from '@/api/types'
import { isValidPortalUrl } from '@/lib/listingFidelity'

type Props = {
  onClose: () => void
  onAdded: (item: InterestItem) => void
}

/** iter-9 — pegar una URL de cualquier portal y sumarla a Intereses. */
export function AddExternalListingModal({ onClose, onAdded }: Props) {
  const [url, setUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const valid = isValidPortalUrl(url)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!valid || submitting) return
    setSubmitting(true)
    setError(null)
    try {
      const item = await interestApi.createExternal({ url: url.trim() })
      onAdded(item)
      onClose()
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError('Esta publicación ya está en tus intereses.')
        } else if (err.code === 'unsupported_url') {
          setError('La URL no es válida. Revisá que sea un link http(s) a una publicación.')
        } else if (err.code === 'extract_failed') {
          setError('No pudimos leer los datos de esa publicación. Probá con otra URL.')
        } else {
          setError(err.message || 'No se pudo agregar la publicación.')
        }
      } else {
        setError('No se pudo agregar la publicación.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-external-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-lg border border-line bg-surface p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="add-external-title" className="font-display text-2xl font-bold text-ink">
          Agregar publicación externa
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          Pegá el link de una publicación de cualquier portal. Extraemos los datos y la
          sumamos a tus intereses con su ficha y reporte.
        </p>

        <form onSubmit={submit} className="mt-4 space-y-3">
          <label htmlFor="external-url" className="block text-sm font-medium text-ink">
            URL de la publicación
          </label>
          <input
            id="external-url"
            type="url"
            autoFocus
            className="hh-input w-full"
            placeholder="https://…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={submitting}
          />

          {error && (
            <p className="text-sm text-danger" role="alert">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              className="hh-btn-ghost text-sm"
              onClick={onClose}
              disabled={submitting}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="hh-btn-primary text-sm"
              disabled={!valid || submitting}
            >
              {submitting ? 'Agregando…' : 'Agregar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
