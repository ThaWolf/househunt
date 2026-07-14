import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { authApi } from '@/api/endpoints'
import { useAuth } from '@/auth/AuthContext'

export function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/search'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (!loading && isAuthenticated) {
    return <Navigate to={from} replace />
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'No se pudo iniciar sesión',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md animate-fade-in">
      <h1 className="font-display text-4xl font-bold text-ink mb-1">Entrar</h1>
      <p className="text-sm text-ink-muted mb-6">
        Househunt — búsqueda unificada GBA / nacional
      </p>

      <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-line bg-surface p-5">
        <div>
          <label className="hh-label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            className="hh-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <label className="hh-label" htmlFor="password">
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
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
          {busy ? 'Entrando…' : 'Entrar'}
        </button>
        <a
          href={authApi.googleStartUrl()}
          className="hh-btn-ghost w-full no-underline"
        >
          Continuar con Google
        </a>
      </form>

      <p className="mt-4 text-sm text-ink-muted text-center">
        ¿Sin cuenta?{' '}
        <Link to="/register" className="text-accent">
          Registrarse
        </Link>
      </p>
    </div>
  )
}
