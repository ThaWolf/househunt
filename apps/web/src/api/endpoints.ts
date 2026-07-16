import { apiRequest } from '@/api/client'
import type {
  AdaptersMetaResponse,
  AuthResponse,
  CalendarResponse,
  CalendarSyncResponse,
  CreateInterestRequest,
  ExternalInterestRequest,
  GeoSuggestResponse,
  InterestListResponse,
  InterestItem,
  InterestListsResponse,
  ListMember,
  LoginRequest,
  PatchInterestRequest,
  PropertyDetailResponse,
  RegisterRequest,
  SearchFilters,
  SearchResponse,
  User,
  Visit,
} from '@/api/types'

export const authApi = {
  register: (body: RegisterRequest) =>
    apiRequest<AuthResponse>('/api/auth/register', {
      method: 'POST',
      body,
      auth: false,
    }),
  login: (body: LoginRequest) =>
    apiRequest<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body,
      auth: false,
    }),
  logout: () =>
    apiRequest<void>('/api/auth/logout', { method: 'POST' }),
  me: () => apiRequest<User>('/api/auth/me'),
  /** Backend redirect flow — navigate browser here. */
  googleStartUrl: () => '/api/auth/google',
}

export const searchApi = {
  search: (filters: SearchFilters) =>
    apiRequest<SearchResponse>('/api/search', {
      method: 'POST',
      body: filters,
    }),
}

export const geoApi = {
  suggest: (q: string, signal?: AbortSignal) =>
    apiRequest<GeoSuggestResponse>(
      `/api/geo/suggest?q=${encodeURIComponent(q)}`,
      { signal },
    ),
}

export const propertiesApi = {
  get: (propertyId: string, listId?: string) => {
    const q = listId ? `?listId=${encodeURIComponent(listId)}` : ''
    return apiRequest<PropertyDetailResponse>(`/api/properties/${propertyId}${q}`)
  },
  putVisit: (propertyId: string, visit: Visit, listId?: string) =>
    apiRequest<Visit>(`/api/properties/${propertyId}/visit`, {
      method: 'PUT',
      body: listId ? { ...visit, listId } : visit,
    }),
}

export const interestListsApi = {
  list: () => apiRequest<InterestListsResponse>('/api/interest/lists'),
  get: (listId: string) =>
    apiRequest<{ id: string; name: string; ownerUserId: string; members: ListMember[] }>(
      `/api/interest/lists/${listId}`,
    ),
  invite: (listId: string, email: string) =>
    apiRequest<ListMember>(`/api/interest/lists/${listId}/members`, {
      method: 'POST',
      body: { email },
    }),
  removeMember: (listId: string, userId: string) =>
    apiRequest<void>(`/api/interest/lists/${listId}/members/${userId}`, {
      method: 'DELETE',
    }),
}

export const interestApi = {
  list: (
    state: 'active' | 'archived' = 'active',
    limit = 50,
    offset = 0,
    listId?: string,
  ) => {
    const params = new URLSearchParams({
      state,
      limit: String(limit),
      offset: String(offset),
    })
    if (listId) params.set('listId', listId)
    return apiRequest<InterestListResponse>(`/api/interest?${params}`)
  },
  create: (body: CreateInterestRequest) =>
    apiRequest<InterestItem>('/api/interest', { method: 'POST', body }),
  createExternal: (body: ExternalInterestRequest) =>
    apiRequest<InterestItem>('/api/interest/external', {
      method: 'POST',
      body,
    }),
  patch: (interestId: string, body: PatchInterestRequest) =>
    apiRequest<InterestItem>(`/api/interest/${interestId}`, {
      method: 'PATCH',
      body,
    }),
  archive: (interestId: string) =>
    apiRequest<InterestItem>(`/api/interest/${interestId}/archive`, {
      method: 'POST',
    }),
  restore: (interestId: string) =>
    apiRequest<InterestItem>(`/api/interest/${interestId}/restore`, {
      method: 'POST',
    }),
}

export const calendarApi = {
  list: (from: string, to: string, listId?: string) => {
    const params = new URLSearchParams({
      from,
      to,
    })
    if (listId) params.set('listId', listId)
    return apiRequest<CalendarResponse>(`/api/calendar?${params}`)
  },
  sync: (interestIds?: string[], listId?: string) =>
    apiRequest<CalendarSyncResponse>('/api/calendar/sync', {
      method: 'POST',
      body: {
        ...(interestIds ? { interestIds } : {}),
        ...(listId ? { listId } : {}),
      },
    }),
}

export const metaApi = {
  adapters: () => apiRequest<AdaptersMetaResponse>('/api/meta/adapters'),
  health: () =>
    apiRequest<{ status: string; version?: string }>('/api/health', {
      auth: false,
    }),
}
