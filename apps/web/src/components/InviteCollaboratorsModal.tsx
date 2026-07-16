import { useState } from 'react'
import { ApiError } from '@/api/client'
import { interestListsApi } from '@/api/endpoints'
import { useActiveList } from '@/context/ActiveListContext'

type Props = {
  onClose: () => void
}

export function InviteCollaboratorsModal({ onClose }: Props) {
  const { activeListId, activeList, refreshLists } = useActiveList()
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)

  if (!activeListId || activeList?.role !== 'owner') {
    return null
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setSending(true)
    setError(null)
    setSuccess(null)
    try {
      const member = await interestListsApi.invite(activeListId!, email.trim())
      setSuccess(`Invitado: ${member.email}`)
      setEmail('')
      await refreshLists()
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('No se pudo invitar')
      }
    } finally {
      setSending(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="invite-title"
    >
      <div className="w-full max-w-md rounded-lg border border-line bg-surface p-5 shadow-lg">
        <h2 id="invite-title" className="font-display text-xl font-bold text-ink mb-2">
          Invitar colaborador
        </h2>
        <p className="text-sm text-ink-muted mb-4">
          La persona debe tener cuenta en Househunt (mismo email de registro).
        </p>
        <form onSubmit={(e) => void submit(e)} className="space-y-3">
          <input
            type="email"
            className="hh-input w-full"
            placeholder="email@ejemplo.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          {error && (
            <p className="text-sm text-danger" role="alert">
              {error}
            </p>
          )}
          {success && (
            <p className="text-sm text-accent" role="status">
              {success}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" className="hh-btn-ghost" onClick={onClose}>
              Cerrar
            </button>
            <button type="submit" className="hh-btn-accent" disabled={sending}>
              {sending ? 'Enviando…' : 'Invitar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
