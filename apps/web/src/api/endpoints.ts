import { apiRequest } from '@/api/client'
import type {
  AdaptersMetaResponse,
  AuthResponse,
  CalendarResponse,
  CalendarSyncResponse,
  CreateInterestRequest,
  InterestListResponse,
  InterestItem,
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

export const propertiesApi = {
  get: (propertyId: string) =>
    apiRequest<PropertyDetailResponse>(`/api/properties/${propertyId}`),
  putVisit: (propertyId: string, visit: Visit) =>
    apiRequest<Visit>(`/api/properties/${propertyId}/visit`, {
      method: 'PUT',
      body: visit,
    }),
}

export const interestApi = {
  list: (state: 'active' | 'archived' = 'active', limit = 50, offset = 0) =>
    apiRequest<InterestListResponse>(
      `/api/interest?state=${state}&limit=${limit}&offset=${offset}`,
    ),
  create: (body: CreateInterestRequest) =>
    apiRequest<InterestItem>('/api/interest', { method: 'POST', body }),
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
  list: (from: string, to: string) =>
    apiRequest<CalendarResponse>(
      `/api/calendar?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`,
    ),
  sync: (interestIds?: string[]) =>
    apiRequest<CalendarSyncResponse>('/api/calendar/sync', {
      method: 'POST',
      body: interestIds ? { interestIds } : {},
    }),
}

export const metaApi = {
  adapters: () => apiRequest<AdaptersMetaResponse>('/api/meta/adapters'),
  health: () =>
    apiRequest<{ status: string; version?: string }>('/api/health', {
      auth: false,
    }),
}
