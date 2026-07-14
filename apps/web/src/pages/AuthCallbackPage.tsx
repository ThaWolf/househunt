import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { LoadingState, ErrorState } from '@/components/LoadingState'

/**
 * Handles Google OAuth callback:
 * `/auth/callback#accessToken=…&refreshToken=…`
 */
export function AuthCallbackPage() {
  const { acceptTokens } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const hash = window.location.hash.replace(/^#/, '')
    const params = new URLSearchParams(hash)
    const accessToken = params.get('accessToken')
    const refreshToken = params.get('refreshToken')

    // Also accept query params as fallback
    const q = new URLSearchParams(window.location.search)
    const access = accessToken ?? q.get('accessToken')
    const refresh = refreshToken ?? q.get('refreshToken')

    if (!access || !refresh) {
      setError('Faltan tokens en el callback de Google')
      return
    }

    void acceptTokens(access, refresh)
      .then(() => {
        window.history.replaceState(null, '', '/auth/callback')
        navigate('/search', { replace: true })
      })
      .catch(() => setError('No se pudo completar el login con Google'))
  }, [acceptTokens, navigate])

  if (error) {
    return (
      <ErrorState
        title="Auth falló"
        message={error}
        onRetry={() => navigate('/login')}
      />
    )
  }

  return <LoadingState label="Completando login con Google…" />
}
