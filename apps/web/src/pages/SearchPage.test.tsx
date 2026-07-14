import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { SearchPage } from '@/pages/SearchPage'

vi.mock('@/api/endpoints', () => ({
  searchApi: {
    search: vi.fn(),
  },
  geoApi: {
    suggest: vi.fn().mockResolvedValue({
      items: [
        {
          label: 'Manuel B. Gonnet, La Plata, Buenos Aires',
          query: 'Manuel B. Gonnet, La Plata, Buenos Aires',
          locality: 'Gonnet',
          district: 'La Plata',
          province: 'Buenos Aires',
          country: 'AR',
          placeId: 'ar-gonnet',
        },
      ],
    }),
  },
}))

describe('SearchPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows Ubicación / localidad label and not Barrio', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    render(
      <MemoryRouter>
        <SearchPage />
      </MemoryRouter>,
    )

    expect(screen.getByLabelText(/Ubicación \/ localidad/i)).toBeInTheDocument()
    expect(screen.queryByText(/^Barrio/)).not.toBeInTheDocument()
    expect(screen.getByLabelText(/Habitaciones mín/i)).toBeInTheDocument()

    await user.type(screen.getByLabelText(/Ubicación \/ localidad/i), 'Gon')
    await vi.advanceTimersByTimeAsync(300)

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /Manuel B\. Gonnet/i }),
      ).toBeInTheDocument()
    })
  })
})
