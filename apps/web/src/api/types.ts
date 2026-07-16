/** DTOs aligned to factory design API_CONTRACT.md iter 5 (camelCase wire). */

export type PortalId =
  | 'zonaprop'
  | 'argenprop'
  | 'mercadolibre'
  | 'remax'
  | 'century21'
  | 'external'

export type Operation = 'buy'
export type PropertyType = 'house' | 'apartment' | 'land' | 'other'
export type Currency = 'USD' | 'ARS'
export type InterestState = 'active' | 'archived'
export type VisitStatus = 'none' | 'scheduled' | 'visited'
export type AdapterStatus = 'ok' | 'partial' | 'error' | 'skipped'
/** E23/E25 — adapter maturity for ops + diagnostics. */
export type AdapterMaturity =
  | 'live_ok'
  | 'live_partial'
  | 'not_implemented'
  | 'broken'
export type AdapterErrorCode =
  | 'bot_wall'
  | 'rate_limit'
  | 'parse'
  | 'network'
  | 'not_implemented'
  | 'fixtures_only'
  | 'auth_required'
  | 'filtered_rooms_null'
/** E23 — empty search UX kind. */
export type EmptyStateKind =
  | 'ok'
  | 'no_inventory'
  | 'rooms_filter_wipe'
  | 'all_partial'
  | 'all_skipped'
  | 'all_error'

/** Canonical id is riskSafety; legacy wire `risk` accepted and normalized in UI. */
export type ScoreComponentId =
  | 'attrs'
  | 'area'
  | 'zone'
  | 'priceFit'
  | 'riskSafety'
  | 'risk'

export type PriceStance = 'low' | 'fair' | 'high' | 'unknown'
/** E19 — required on every ImageRef. */
export type ImageKind = 'source' | 'proxied' | 'placeholder'
/** E17 — required on Property. FE alias listingFidelity ≡ same values. */
export type DataSource = 'live' | 'fixture_curated' | 'demo_stub' | 'external'
export type DataSourceHint = DataSource | 'mixed'
export type ZonePlaceSource = 'seed' | 'places' | 'stub'
export type ZoneProvider = 'none' | 'seed' | 'google_places'
export type GeocodeStatus = 'exact' | 'approximate' | 'missing' | 'stub'
export type GeocodeSource = 'portal' | 'seed_locality' | 'places' | 'manual'
export type MapPinKind = 'listing' | 'poi' | 'commerce' | 'transit'
export type MapProvider = 'google_embed' | 'external_only'
export type SearchModeHint = 'fixtures' | 'live' | 'hybrid'

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
  /** E19 — required on wire; missing treated as placeholder in UI. */
  kind: ImageKind
}

export interface Agent {
  name: string | null
  phone: string | null
}

export interface ScoreComponent {
  id: ScoreComponentId
  label: string
  /** E12 — required on wire; FE falls back to SCORE_COMPONENT_COPY if omitted */
  helpText?: string
  score: number
  maxScore: number
  barPct: number
  /** 1-line evidence (preferred) */
  summary?: string | null
  /** Legacy alias of summary */
  note?: string | null
}

export interface RiskHit {
  /** Canonical wire field */
  keyword?: string
  weight?: number
  label?: string | null
  /** Legacy alias → keyword */
  term?: string
}

export interface PriceNarrative {
  summary: string
  stance: PriceStance
  peersSampleSize: number
  peerMedianAmount?: number | null
  currency?: Currency | null
}

export interface ZonePlace {
  id: string
  name: string
  category: string
  lat?: number | null
  lng?: number | null
  distanceM?: number | null
  source: ZonePlaceSource
}

export interface ZoneReport {
  summary?: string | null
  poi: ZonePlace[]
  commerce: ZonePlace[]
  transit: ZonePlace[]
  geo: {
    lat?: number | null
    lng?: number | null
    geocodeStatus: GeocodeStatus
    geocodeSource?: GeocodeSource | null
  }
  generatedAt: string
  provider: ZoneProvider
}

export interface MapPin {
  id: string
  lat: number
  lng: number
  label: string
  kind: MapPinKind
}

export interface MapEmbed {
  center: { lat: number; lng: number }
  zoom?: number | null
  pins: MapPin[]
  embedUrl?: string | null
  externalUrl: string
  provider: MapProvider
}

export interface HumanizedReport {
  summary: string | null
  appScore: number
  components: ScoreComponent[]
  riskHits: RiskHit[]
  priceNarrative?: PriceNarrative | null
  zoneReport?: ZoneReport | null
  map?: MapEmbed | null
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
  /**
   * E17 — required. live | fixture_curated | demo_stub.
   * Missing on wire → FE treats as non-live (badge + CTA rules).
   */
  dataSource: DataSource
  /** Display alias of dataSource (same enum); prefer dataSource on wire. */
  listingFidelity?: DataSource
  title: string
  /** Full listing text when available (E13). */
  description: string | null
  /** Optional teaser ≤ ~280 chars for cards — does not replace description. */
  descriptionExcerpt?: string | null
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

export interface AddedByUser {
  userId: string
  displayName: string | null
  email: string
}

export interface InterestListSummary {
  id: string
  name: string
  role: 'owner' | 'collaborator'
  memberCount: number
}

export interface InterestListsResponse {
  items: InterestListSummary[]
}

export interface ListMember {
  userId: string
  email: string
  displayName: string | null
  role: 'owner' | 'collaborator'
  joinedAt: string
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
  maxPages?: number | null
  pageSizeHint?: number | null
}

export interface AdapterPaginationMeta {
  pagesFetched?: number
  listingsRaw?: number
  listingsAfterFilter?: number
  maxPages?: number
  pageSizeHint?: number
  mode?: SearchModeHint | null
  dataSourceHint?: DataSourceHint | null
}

export interface PortalDiagnostics {
  rawCount: number
  afterFilterCount: number
  roomsDropped: number
  roomsFilterWiped: boolean
  maturity: AdapterMaturity
  dropReasons?: Array<
    'rooms_null' | 'rooms_below_min' | 'geo' | 'price' | 'other'
  >
}

export interface PortalSearchResult {
  portal: PortalId
  status: AdapterStatus
  /** Mirror of diagnostics.maturity (E23 convenience). */
  maturity?: AdapterMaturity
  count?: number
  unsupportedFilters?: string[]
  pagination?: AdapterPaginationMeta | null
  diagnostics?: PortalDiagnostics
  error?: {
    code: AdapterErrorCode
    message: string
    retryable: boolean
  } | null
}

export interface EmptyStateHint {
  kind: EmptyStateKind
  title: string
  body: string
  hint?: string | null
}

export interface SearchDiagnosticsPortalRow {
  portal: PortalId
  rawCount: number
  afterFilterCount: number
  roomsDropped: number
  roomsFilterWiped: boolean
  maturity: AdapterMaturity
  status: AdapterStatus
  errorCode?: AdapterErrorCode | null
}

/** E23 — required on SearchResponse i5. */
export interface SearchDiagnostics {
  rawCount: number
  afterFilterCount: number
  roomsDropped: number
  roomsFilterWiped: boolean
  portals: SearchDiagnosticsPortalRow[]
  /** Required when items.length === 0; null when items > 0. */
  emptyState?: EmptyStateHint | null
}

export interface SearchResultItem extends Property {
  interest?: InterestFlags | null
}

export interface SearchResponse {
  searchId: string
  filters: SearchFilters
  items: SearchResultItem[]
  portalResults: PortalSearchResult[]
  /** E23 — required i5; optional for session payloads from older iters. */
  diagnostics?: SearchDiagnostics
  density?: {
    totalItems?: number
    portalsWithMultiPage?: number
    mode?: SearchModeHint
    dataSourceHint?: DataSourceHint | null
  } | null
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
  addedBy?: AddedByUser | null
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
  listId?: string
}

export interface ExternalInterestRequest {
  url: string
  listId?: string
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
    maturity?: AdapterMaturity
    analysisStatus: string
    hybridDefault?: boolean
  }>
  features: {
    googleCalendar?: boolean
    googleMaps?: boolean
    imageProxy?: boolean
    poi?: boolean
    hybridAdapters?: boolean
  }
}

/** Canonical empty-state copy (E23) when BE omits emptyState but items=[]. */
export const EMPTY_STATE_COPY: Record<
  Exclude<EmptyStateKind, 'ok'>,
  { title: string; body: string; hint?: string }
> = {
  rooms_filter_wipe: {
    title: 'Sin resultados con ese filtro de ambientes',
    body: 'Encontramos avisos, pero ninguno pasó el mínimo de habitaciones (faltaba dato o eran menos). Probá bajar ambientes o buscar sin mínimo.',
    hint: 'Bajá el mínimo de habitaciones o quitá el filtro.',
  },
  no_inventory: {
    title: 'Sin avisos en esta zona',
    body: 'Los portales no devolvieron inventario para esta búsqueda.',
  },
  all_partial: {
    title: 'Búsqueda incompleta',
    body: 'Varios portales respondieron parcial; no hay listados que cumplan los filtros.',
  },
  all_skipped: {
    title: 'Portales no disponibles',
    body: 'Los scrapers están deshabilitados o aún no implementados.',
  },
  all_error: {
    title: 'No pudimos consultar portales',
    body: 'Errores de red, anti-bot o auth. Reintentá en unos minutos.',
  },
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
  external: 'Externa',
}

/** Canonical labels / helpText when BE omits them (E11–E12). */
export const SCORE_COMPONENT_COPY: Record<
  Exclude<ScoreComponentId, 'risk'>,
  { label: string; helpText: string }
> = {
  attrs: {
    label: 'Atributos',
    helpText:
      'Habitaciones, baños, cochera y comodidades, comparado con lo esperable para una casa.',
  },
  area: {
    label: 'Superficie',
    helpText:
      'Metros cubiertos y de terreno, comparado con casas parecidas de la zona.',
  },
  zone: {
    label: 'Zona',
    helpText:
      'Qué tan movida está la zona: comercios, transporte y lugares cerca del inmueble.',
  },
  priceFit: {
    label: 'Ajuste de precio',
    helpText:
      'Si el precio está barato, caro o en su punto para casas parecidas de la zona.',
  },
  riskSafety: {
    label: 'Seguridad',
    helpText:
      'Buscamos alertas en el texto del aviso (para refaccionar, humedad, temas legales). 100 = sin alertas; más bajo = más señales para revisar.',
  },
}

export function normalizeScoreComponentId(
  id: ScoreComponentId,
): Exclude<ScoreComponentId, 'risk'> {
  return id === 'risk' ? 'riskSafety' : id
}
