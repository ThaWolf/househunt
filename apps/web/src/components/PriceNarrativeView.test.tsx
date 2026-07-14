import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PriceNarrativeView } from '@/components/PriceNarrativeView'

describe('PriceNarrativeView', () => {
  it('renders summary and stance', () => {
    render(
      <PriceNarrativeView
        narrative={{
          summary: 'El precio está por debajo del promedio de 6 avisos similares.',
          stance: 'low',
          peersSampleSize: 6,
          peerMedianAmount: 140000,
          currency: 'USD',
        }}
      />,
    )
    expect(screen.getByText(/por debajo del promedio/i)).toBeInTheDocument()
    expect(screen.getByText(/Por debajo del cohort/i)).toBeInTheDocument()
    expect(screen.getByText('6')).toBeInTheDocument()
  })

  it('renders nothing when narrative missing', () => {
    const { container } = render(<PriceNarrativeView narrative={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
