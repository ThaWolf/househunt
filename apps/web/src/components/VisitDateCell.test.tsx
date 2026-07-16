import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { VisitDateCell } from '@/components/VisitDateCell'

describe('VisitDateCell', () => {
  it('shows em dash for none', () => {
    render(<VisitDateCell visit={{ status: 'none', at: null }} />)
    expect(screen.getByText('—')).toBeTruthy()
  })

  it('formats scheduled datetime', () => {
    render(
      <VisitDateCell
        visit={{ status: 'scheduled', at: '2026-07-20T15:30:00.000Z' }}
      />,
    )
    expect(screen.getByText(/20\/07\/2026/)).toBeTruthy()
  })

  it('prefixes visited', () => {
    render(
      <VisitDateCell visit={{ status: 'visited', at: '2026-07-20T15:30:00.000Z' }} />,
    )
    expect(screen.getByText(/Visitada:/)).toBeTruthy()
  })
})
