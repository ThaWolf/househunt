import type { ErrorResponse } from '@/api/types'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from '@/auth/tokens'

export class ApiError extends Error {
  status: number
  code: string
  details: Record<string, unknown> | null

  constructor(status: number, body: ErrorResponse | string) {
    if (typeof body === 'string') {
      super(body)
      this.code = 'unknown'
      this.details = null
    } else {
      super(body.message)
      this.code = body.code
      this.details = body.details ?? null
    }
    this.status = status
    this.name = 'ApiError'
  }
}

type RequestOptions = {
  method?: string
  body?: unknown
  auth?: boolean
  signal?: AbortSignal
}

let refreshPromise: Promise<boolean> | null = null

async function tryRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return false

  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    })
    if (!res.ok) {
      clearTokens()
      return false
    }
    const data = (await res.json()) as {
      accessToken: string
      refreshToken: string
    }
    setTokens(data.accessToken, data.refreshToken)
    return true
  } catch {
    clearTokens()
    return false
  }
}

function refreshOnce(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = tryRefresh().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, auth = true, signal } = options

  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth) {
    const token = getAccessToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const doFetch = () =>
    fetch(path.startsWith('/api') ? path : `/api${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    })

  let res = await doFetch()

  if (res.status === 401 && auth) {
    const ok = await refreshOnce()
    if (ok) {
      const token = getAccessToken()
      if (token) headers.Authorization = `Bearer ${token}`
      res = await doFetch()
    }
  }

  if (res.status === 204) return undefined as T

  const text = await res.text()
  let parsed: unknown = null
  if (text) {
    try {
      parsed = JSON.parse(text)
    } catch {
      parsed = text
    }
  }

  if (!res.ok) {
    if (parsed && typeof parsed === 'object' && 'code' in parsed) {
      throw new ApiError(res.status, parsed as ErrorResponse)
    }
    throw new ApiError(res.status, typeof parsed === 'string' ? parsed : res.statusText)
  }

  return parsed as T
}

/** Injectable for tests / mocks. */
export type ApiClient = typeof api

export const api = {
  request: apiRequest,
}
