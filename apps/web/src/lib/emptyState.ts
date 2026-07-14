import {
  EMPTY_STATE_COPY,
  type AdapterStatus,
  type EmptyStateHint,
  type EmptyStateKind,
  type PortalSearchResult,
  type SearchDiagnostics,
  type SearchResponse,
} from '@/api/types'

function deriveKind(
  diagnostics: SearchDiagnostics | undefined,
  portalResults: PortalSearchResult[],
): Exclude<EmptyStateKind, 'ok'> {
  if (diagnostics?.roomsFilterWiped) return 'rooms_filter_wipe'
  if (diagnostics?.portals.some((p) => p.roomsFilterWiped)) {
    return 'rooms_filter_wipe'
  }
  if (
    portalResults.some(
      (p) =>
        p.diagnostics?.roomsFilterWiped ||
        p.error?.code === 'filtered_rooms_null',
    )
  ) {
    return 'rooms_filter_wipe'
  }

  const statuses = portalResults.map((p) => p.status)
  if (statuses.length && statuses.every((s) => s === 'skipped')) {
    return 'all_skipped'
  }
  if (statuses.length && statuses.every((s) => s === 'error')) {
    return 'all_error'
  }
  if (
    statuses.length &&
    statuses.every((s) => s === 'partial' || s === 'error' || s === 'skipped')
  ) {
    return 'all_partial'
  }

  const raw =
    diagnostics?.rawCount ??
    portalResults.reduce(
      (n, p) =>
        n +
        (p.diagnostics?.rawCount ??
          p.pagination?.listingsRaw ??
          0),
      0,
    )
  if (raw > 0) return 'all_partial'
  return 'no_inventory'
}

/** Resolve emptyState for UI when items.length === 0 (E23). */
export function resolveEmptyState(
  response: Pick<SearchResponse, 'items' | 'portalResults' | 'diagnostics'>,
): EmptyStateHint | null {
  if (response.items.length > 0) return null

  const fromWire = response.diagnostics?.emptyState
  if (fromWire?.kind && fromWire.kind !== 'ok' && fromWire.title) {
    return {
      kind: fromWire.kind,
      title: fromWire.title,
      body: fromWire.body,
      hint: fromWire.hint ?? null,
    }
  }

  const kind = deriveKind(response.diagnostics, response.portalResults)
  const copy = EMPTY_STATE_COPY[kind]
  return {
    kind,
    title: copy.title,
    body: copy.body,
    hint: copy.hint ?? null,
  }
}

export type PortalCountRow = {
  portal: PortalSearchResult['portal']
  status: AdapterStatus
  rawCount: number | null
  afterFilterCount: number | null
  roomsDropped: number | null
  roomsFilterWiped: boolean
  maturity?: string | null
}

/** Prefer diagnostics.portals; fallback to portalResults diagnostics/pagination. */
export function portalCountRows(
  response: Pick<SearchResponse, 'portalResults' | 'diagnostics'>,
): PortalCountRow[] {
  const diagMap = new Map(
    (response.diagnostics?.portals ?? []).map((p) => [p.portal, p]),
  )

  return response.portalResults.map((pr) => {
    const row = diagMap.get(pr.portal)
    const raw =
      row?.rawCount ??
      pr.diagnostics?.rawCount ??
      pr.pagination?.listingsRaw ??
      null
    const after =
      row?.afterFilterCount ??
      pr.diagnostics?.afterFilterCount ??
      pr.pagination?.listingsAfterFilter ??
      pr.count ??
      null
    return {
      portal: pr.portal,
      status: row?.status ?? pr.status,
      rawCount: raw,
      afterFilterCount: after,
      roomsDropped:
        row?.roomsDropped ?? pr.diagnostics?.roomsDropped ?? null,
      roomsFilterWiped:
        row?.roomsFilterWiped ??
        pr.diagnostics?.roomsFilterWiped ??
        false,
      maturity:
        row?.maturity ??
        pr.maturity ??
        pr.diagnostics?.maturity ??
        null,
    }
  })
}
