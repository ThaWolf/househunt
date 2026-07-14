import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { authApi } from '@/api/endpoints'
import { ApiError } from '@/api/client'
import type { User } from '@/api/types'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from '@/auth/tokens'

type AuthState = {
  user: User | null
  loading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (
    email: string,
    password: string,
    displayName?: string,
  ) => Promise<void>
  logout: () => Promise<void>
  acceptTokens: (accessToken: string, refreshToken: string) => Promise<void>
  refreshSession: () => Promise<boolean>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const loadMe = useCallback(async () => {
    if (!getAccessToken() && !getRefreshToken()) {
      setUser(null)
      return false
    }
    try {
      if (!getAccessToken() && getRefreshToken()) {
        const res = await fetch('/api/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refreshToken: getRefreshToken() }),
        })
        if (!res.ok) {
          clearTokens()
          setUser(null)
          return false
        }
        const data = (await res.json()) as {
          accessToken: string
          refreshToken: string
        }
        setTokens(data.accessToken, data.refreshToken)
      }
      const me = await authApi.me()
      setUser(me)
      return true
    } catch {
      clearTokens()
      setUser(null)
      return false
    }
  }, [])

  useEffect(() => {
    void loadMe().finally(() => setLoading(false))
  }, [loadMe])

  const acceptTokens = useCallback(
    async (accessToken: string, refreshToken: string) => {
      setTokens(accessToken, refreshToken)
      const me = await authApi.me()
      setUser(me)
    },
    [],
  )

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login({ email, password })
    setTokens(res.accessToken, res.refreshToken)
    setUser(res.user)
  }, [])

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const res = await authApi.register({
        email,
        password,
        displayName: displayName ?? null,
      })
      setTokens(res.accessToken, res.refreshToken)
      setUser(res.user)
    },
    [],
  )

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } catch (e) {
      if (!(e instanceof ApiError)) throw e
    } finally {
      clearTokens()
      setUser(null)
    }
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      acceptTokens,
      refreshSession: loadMe,
    }),
    [user, loading, login, register, logout, acceptTokens, loadMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
