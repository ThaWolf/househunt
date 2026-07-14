import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { authApi } from '@/api/endpoints'
import { useAuth } from '@/auth/AuthContext'

export function RegisterPage() {
  const { register, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!loading && isAuthenticated) {
    return <Navigate to="/search" replace />
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres')
      return
    }
    setBusy(true)
    try {
      await register(email, password, displayName || undefined)
      navigate('/search', { replace: true })
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'No se pudo registrar',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md animate-fade-in">
      <h1 className="font-display text-4xl font-bold text-ink mb-1">
        Crear cuenta
      </h1>
      <p className="text-sm text-ink-muted mb-6">Househunt</p>

      <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-line bg-surface p-5">
        <div>
          <label className="hh-label" htmlFor="displayName">
            Nombre (opcional)
          </label>
          <input
            id="displayName"
            className="hh-input"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </div>
        <div>
          <label className="hh-label" htmlFor="reg-email">
            Email
          </label>
          <input
            id="reg-email"
            type="email"
            required
            className="hh-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <label className="hh-label" htmlFor="reg-password">
            Contraseña (mín. 8)
          </label>
          <input
            id="reg-password"
            type="password"
            required
            minLength={8}
            className="hh-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && (
          <p className="text-sm text-danger" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="hh-btn-primary w-full" disabled={busy}>
          {busy ? 'Creando…' : 'Registrarse'}
        </button>
        <a
          href={authApi.googleStartUrl()}
          className="hh-btn-ghost w-full no-underline"
        >
          Continuar con Google
        </a>
      </form>

      <p className="mt-4 text-sm text-ink-muted text-center">
        ¿Ya tenés cuenta?{' '}
        <Link to="/login" className="text-accent">
          Entrar
        </Link>
      </p>
    </div>
  )
}
