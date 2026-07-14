/** DTOs aligned to factory design API_CONTRACT.md iter 2 (camelCase wire). */

export type PortalId =
  | 'zonaprop'
  | 'argenprop'
  | 'mercadolibre'
  | 'remax'
  | 'century21'

export type Operation = 'buy'
export type PropertyType = 'house' | 'apartment' | 'land' | 'other'
export type Currency = 'USD' | 'ARS'
export type InterestState = 'active' | 'archived'
export type VisitStatus = 'none' | 'scheduled' | 'visited'
export type AdapterStatus = 'ok' | 'partial' | 'error' | 'skipped'
export type AdapterErrorCode =
  | 'bot_wall'
  | 'rate_limit'
  | 'parse'
  | 'network'
  | 'not_implemented'
  | 'fixtures_only'

export type ScoreComponentId = 'attrs' | 'area' | 'zone' | 'priceFit' | 'risk'

export interface Money {
  amount: number | null
  currency: Currency | null
  period: null
}

export interface Address {
  raw: string | null
  province: string | null
  locality: string | null
  neighborhood: string | null
}

export interface GeoPoint {
  lat: number | null
  lng: number | null
}

export interface Area {
  coveredM2: number | null
  totalM2: number | null
}

export interface ImageRef {
  url: string
  order: number
}

export interface Agent {
  name: string | null
  phone: string | null
}

export interface ScoreComponent {
  id: ScoreComponentId
  label: string
  score: number
  maxScore: number
  barPct: number
  note?: string | null
}

export interface RiskHit {
  term: string
  label: string
}

export interface HumanizedReport {
  summary: string | null
  appScore: number
  components: ScoreComponent[]
  riskHits: RiskHit[]
  generatedAt: string
}

export interface Location {
  query: string
  locality: string
  district?: string | null
  province: string
  country: 'AR'
  placeId?: string | null
}

export interface GeoPlace extends Location {
  label: string
  aliases?: string[]
}

export interface Property {
  id: string
  portal: PortalId
  externalId: string
  sourceUrl: string
  title: string
  description: string | null
  operation: Operation
  propertyType: PropertyType
  price?: Money
  address?: Address
  geo?: GeoPoint
  rooms: number | null
  bathrooms: number | null
  parking: number | null
  area?: Area
  amenities?: string[]
  images: ImageRef[]
  agent?: Agent
  listedAt: string | null
  scrapedAt: string
  appScore: number | null
}

export interface Visit {
  status: VisitStatus
  at: string | null
}

export interface InterestFlags {
  state: InterestState | null
  userScore?: number | null
  visit?: Visit | null
  comments?: string | null
  commentFlag?: boolean
}

export interface SearchFilters {
  operation: Operation
  propertyType: PropertyType
  /** null/omit → preset GBA (no strict geo post-filter). */
  location?: Location | null
  price?: {
    min?: number | null
    max?: number | null
    currency?: Currency
  }
  rooms?: { min?: number | null }
  bathrooms?: { min?: number | null }
  area?: {
    coveredM2Min?: number | null
    totalM2Min?: number | null
  }
  parking?: { min?: number | null }
  portals?: PortalId[]
  query?: string | null
}

export interface PortalSearchResult {
  portal: PortalId
  status: AdapterStatus
  count?: number
  unsupportedFilters?: string[]
  error?: {
    code: AdapterErrorCode
    message: string
    retryable: boolean
  } | null
}

export interface SearchResultItem extends Property {
  interest?: InterestFlags | null
}

export interface SearchResponse {
  searchId: string
  filters: SearchFilters
  items: SearchResultItem[]
  portalResults: PortalSearchResult[]
  tookMs: number
}

export interface PageMeta {
  total: number
  limit: number
  offset: number
}

export interface ErrorResponse {
  code: string
  message: string
  details?: Record<string, unknown> | null
}

export interface RegisterRequest {
  email: string
  password: string
  displayName?: string | null
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RefreshRequest {
  refreshToken: string
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  tokenType: 'Bearer'
  expiresIn: number
}

export interface User {
  id: string
  email: string
  displayName: string | null
}

export interface AuthResponse extends AuthTokens {
  user: User
}

export interface PropertyDetailResponse {
  property: Property
  interest: InterestFlags
  report: HumanizedReport | null
  userFieldsEnabled: boolean
}

export interface AmenityHighlight {
  token: string
  label: string
  present: boolean
}

export interface InterestItem {
  id: string
  property: Property
  state: InterestState
  rooms: number | null
  amenitiesHighlight: AmenityHighlight[]
  userScore: number | null
  visit: Visit
  comments: string | null
  commentFlag: boolean
  createdAt: string
  updatedAt: string
  archivedAt: string | null
}

export interface InterestListResponse {
  items: InterestItem[]
  meta: PageMeta
}

export interface CreateInterestRequest {
  propertyId: string
}

export interface PatchInterestRequest {
  userScore?: number | null
  comments?: string | null
}

export interface GeoSuggestResponse {
  items: GeoPlace[]
}

export interface CalendarEvent {
  interestId: string
  propertyId: string
  title: string
  sourceUrl: string
  visit: Visit
  googleEventId: string | null
}

export interface CalendarResponse {
  events: CalendarEvent[]
}

export interface CalendarSyncResponse {
  synced: number
  failed: number
  errors?: ErrorResponse[]
}

export interface AdaptersMetaResponse {
  portals: Array<{
    id: PortalId
    enabled: boolean
    analysisStatus: string
  }>
  features: {
    googleCalendar?: boolean
    imageProxy?: boolean
    poi?: boolean
  }
}

export const ALL_PORTALS: PortalId[] = [
  'zonaprop',
  'argenprop',
  'mercadolibre',
  'remax',
  'century21',
]

export const PORTAL_LABELS: Record<PortalId, string> = {
  zonaprop: 'ZonaProp',
  argenprop: 'Argenprop',
  mercadolibre: 'Mercado Libre',
  remax: 'Remax',
  century21: 'Century 21',
}
