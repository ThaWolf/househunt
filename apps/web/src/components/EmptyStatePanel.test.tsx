import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { EmptyStatePanel } from '@/components/EmptyStatePanel'
import { PortalDiagnosticsStrip } from '@/components/PortalDiagnostics'
import { SearchLoadingProgress } from '@/components/LoadingState'
import { ResultsPage } from '@/pages/ResultsPage'
import { LAST_SEARCH_KEY } from '@/pages/SearchPage'
import type { SearchResponse } from '@/api/types'

const wipeResponse: SearchResponse = {
  searchId: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  filters: {
    operation: 'buy',
    propertyType: 'house',
    location: {
      query: 'Gonnet',
      locality: 'Gonnet',
      province: 'Buenos Aires',
      country: 'AR',
    },
    rooms: { min: 3 },
  },
  items: [],
  portalResults: [
    {
      portal: 'zonaprop',
      status: 'partial',
      maturity: 'live_partial',
      count: 0,
      diagnostics: {
        rawCount: 12,
        afterFilterCount: 0,
        roomsDropped: 12,
        roomsFilterWiped: true,
        maturity: 'live_partial',
      },
      error: {
        code: 'filtered_rooms_null',
        message: 'All listings dropped by rooms.min',
        retryable: false,
      },
    },
    {
      portal: 'mercadolibre',
      status: 'partial',
      count: 0,
      pagination: { listingsRaw: 20, listingsAfterFilter: 0 },
      diagnostics: {
        rawCount: 20,
        afterFilterCount: 0,
        roomsDropped: 20,
        roomsFilterWiped: true,
        maturity: 'live_partial',
      },
    },
    {
      portal: 'argenprop',
      status: 'skipped',
      count: 0,
    },
  ],
  diagnostics: {
    rawCount: 32,
    afterFilterCount: 0,
    roomsDropped: 32,
    roomsFilterWiped: true,
    portals: [
      {
        portal: 'zonaprop',
        rawCount: 12,
        afterFilterCount: 0,
        roomsDropped: 12,
        roomsFilterWiped: true,
        maturity: 'live_partial',
        status: 'partial',
        errorCode: 'filtered_rooms_null',
      },
      {
        portal: 'mercadolibre',
        rawCount: 20,
        afterFilterCount: 0,
        roomsDropped: 20,
        roomsFilterWiped: true,
        maturity: 'live_partial',
        status: 'partial',
      },
      {
        portal: 'argenprop',
        rawCount: 0,
        afterFilterCount: 0,
        roomsDropped: 0,
        roomsFilterWiped: false,
        maturity: 'not_implemented',
        status: 'skipped',
      },
    ],
    emptyState: {
      kind: 'rooms_filter_wipe',
      title: 'Sin resultados con ese filtro de ambientes',
      body: 'Encontramos avisos, pero ninguno pasó el mínimo de habitaciones.',
      hint: 'Bajá ambientes',
    },
  },
  tookMs: 12000,
}

describe('EmptyStatePanel', () => {
  it('shows rooms_filter_wipe copy and diagnostics toggle', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <EmptyStatePanel response={wipeResponse} />
      </MemoryRouter>,
    )

    const panel = screen.getByTestId('empty-state-panel')
    expect(panel).toHaveAttribute('data-kind', 'rooms_filter_wipe')
    expect(
      screen.getByText(/Sin resultados con ese filtro de ambientes/i),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/Ningún resultado\. Probá otros filtros/i),
    ).not.toBeInTheDocument()

    await user.click(screen.getByTestId('toggle-diagnostics'))
    expect(screen.getByTestId('diagnostics-panel')).toBeInTheDocument()
    expect(screen.getByTestId('diag-row-zonaprop')).toHaveTextContent(/12/)
    expect(screen.getByTestId('diag-row-mercadolibre')).toHaveTextContent(
      /20/,
    )
  })

  it('falls back to all_partial copy without emptyState wire', () => {
    render(
      <MemoryRouter>
        <EmptyStatePanel
          response={{
            items: [],
            filters: wipeResponse.filters,
            portalResults: [
              { portal: 'zonaprop', status: 'partial' },
              { portal: 'mercadolibre', status: 'error' },
            ],
            diagnostics: undefined,
          }}
        />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('empty-state-panel')).toHaveAttribute(
      'data-kind',
      'all_partial',
    )
    expect(screen.getByText(/Búsqueda incompleta/i)).toBeInTheDocument()
  })
})

describe('PortalDiagnosticsStrip', () => {
  it('renders raw→afterFilter when counts exist', () => {
    render(<PortalDiagnosticsStrip response={wipeResponse} />)
    expect(screen.getByTestId('portal-diagnostics-strip')).toHaveTextContent(
      /ZonaProp.*12→0/,
    )
  })
})

describe('SearchLoadingProgress', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows skeleton and elapsed timer', () => {
    render(<SearchLoadingProgress />)
    expect(screen.getByTestId('search-loading')).toBeInTheDocument()
    expect(screen.getByTestId('search-skeleton')).toBeInTheDocument()
    expect(screen.getByTestId('search-elapsed')).toHaveTextContent('0s')
  })
})

describe('ResultsPage empty', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('renders EmptyStatePanel instead of vague empty success copy', () => {
    sessionStorage.setItem(LAST_SEARCH_KEY, JSON.stringify(wipeResponse))
    render(
      <MemoryRouter>
        <ResultsPage />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('empty-state-panel')).toBeInTheDocument()
    expect(screen.getByText(/0 props/)).toBeInTheDocument()
    expect(
      screen.queryByText(/Ningún resultado\. Probá otros filtros/i),
    ).not.toBeInTheDocument()
  })
})
