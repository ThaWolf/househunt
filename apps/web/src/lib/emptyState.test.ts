import { describe, expect, it } from 'vitest'
import type {
  PortalSearchResult,
  SearchDiagnostics,
  SearchResponse,
} from '@/api/types'
import { portalCountRows, resolveEmptyState } from '@/lib/emptyState'

function portal(
  partial: Partial<PortalSearchResult> & Pick<PortalSearchResult, 'portal'>,
): PortalSearchResult {
  return {
    status: 'partial',
    ...partial,
  }
}

describe('resolveEmptyState', () => {
  it('returns null when there are items', () => {
    expect(
      resolveEmptyState({
        items: [{ id: '1' } as SearchResponse['items'][0]],
        portalResults: [],
        diagnostics: undefined,
      }),
    ).toBeNull()
  })

  it('uses wire emptyState when present', () => {
    const hint = resolveEmptyState({
      items: [],
      portalResults: [portal({ portal: 'zonaprop', status: 'partial' })],
      diagnostics: {
        rawCount: 20,
        afterFilterCount: 0,
        roomsDropped: 20,
        roomsFilterWiped: true,
        portals: [],
        emptyState: {
          kind: 'rooms_filter_wipe',
          title: 'Sin resultados con ese filtro de ambientes',
          body: 'Wire body',
          hint: 'Bajá ambientes',
        },
      },
    })
    expect(hint?.kind).toBe('rooms_filter_wipe')
    expect(hint?.body).toBe('Wire body')
  })

  it('derives rooms_filter_wipe from flag when emptyState missing', () => {
    const hint = resolveEmptyState({
      items: [],
      portalResults: [
        portal({
          portal: 'mercadolibre',
          status: 'partial',
          diagnostics: {
            rawCount: 15,
            afterFilterCount: 0,
            roomsDropped: 15,
            roomsFilterWiped: true,
            maturity: 'live_partial',
          },
        }),
      ],
      diagnostics: {
        rawCount: 15,
        afterFilterCount: 0,
        roomsDropped: 15,
        roomsFilterWiped: true,
        portals: [
          {
            portal: 'mercadolibre',
            rawCount: 15,
            afterFilterCount: 0,
            roomsDropped: 15,
            roomsFilterWiped: true,
            maturity: 'live_partial',
            status: 'partial',
          },
        ],
      },
    })
    expect(hint?.kind).toBe('rooms_filter_wipe')
    expect(hint?.title).toMatch(/ambientes/i)
  })

  it('derives all_partial vs all_skipped vs all_error', () => {
    expect(
      resolveEmptyState({
        items: [],
        portalResults: [
          portal({ portal: 'zonaprop', status: 'partial' }),
          portal({ portal: 'argenprop', status: 'skipped' }),
        ],
        diagnostics: undefined,
      })?.kind,
    ).toBe('all_partial')

    expect(
      resolveEmptyState({
        items: [],
        portalResults: [
          portal({ portal: 'argenprop', status: 'skipped' }),
          portal({ portal: 'remax', status: 'skipped' }),
        ],
        diagnostics: undefined,
      })?.kind,
    ).toBe('all_skipped')

    expect(
      resolveEmptyState({
        items: [],
        portalResults: [
          portal({ portal: 'zonaprop', status: 'error' }),
          portal({ portal: 'century21', status: 'error' }),
        ],
        diagnostics: undefined,
      })?.kind,
    ).toBe('all_error')
  })
})

describe('portalCountRows', () => {
  it('prefers diagnostics.portals then portalResults diagnostics', () => {
    const diagnostics: SearchDiagnostics = {
      rawCount: 10,
      afterFilterCount: 2,
      roomsDropped: 8,
      roomsFilterWiped: false,
      portals: [
        {
          portal: 'zonaprop',
          rawCount: 10,
          afterFilterCount: 2,
          roomsDropped: 8,
          roomsFilterWiped: false,
          maturity: 'live_ok',
          status: 'ok',
        },
      ],
    }
    const rows = portalCountRows({
      diagnostics,
      portalResults: [
        portal({
          portal: 'zonaprop',
          status: 'ok',
          pagination: { listingsRaw: 99, listingsAfterFilter: 99 },
        }),
      ],
    })
    expect(rows[0]).toMatchObject({
      portal: 'zonaprop',
      rawCount: 10,
      afterFilterCount: 2,
    })
  })
})
