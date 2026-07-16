import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  AMENITY_LEGEND,
  AMENITY_UNKNOWN_TOOLTIP,
  AmenityCell,
} from '@/components/AmenityCell'

describe('AmenityCell', () => {
  it('shows em dash when empty', () => {
    render(<AmenityCell items={[]} />)
    expect(screen.getByText('—')).toBeTruthy()
  })

  it('marks confirmed amenities with checkmark', () => {
    render(
      <AmenityCell
        items={[{ token: 'pool', label: 'Pileta', present: true }]}
      />,
    )
    expect(screen.getByText(/✓ Pileta/)).toBeTruthy()
    expect(screen.getByTitle('Pileta')).toBeTruthy()
  })

  it('marks unknown amenities with question mark and honest tooltip', () => {
    render(
      <AmenityCell
        items={[{ token: 'garage', label: 'Cochera', present: false }]}
      />,
    )
    const chip = screen.getByText(/\? Cochera/)
    expect(chip.className).not.toMatch(/line-through/)
    expect(screen.getByTitle(AMENITY_UNKNOWN_TOOLTIP)).toBeTruthy()
  })

  it('exports legend copy for Interest table', () => {
    expect(AMENITY_LEGEND).toMatch(/confirmado/)
    expect(AMENITY_LEGEND).toMatch(/sin dato/)
  })
})
