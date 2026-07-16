import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PriceNarrativeView } from '@/components/PriceNarrativeView'

describe('PriceNarrativeView', () => {
  it('renders friendly summary and typical price without jargon', () => {
    const { container } = render(
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
    expect(screen.getByText(/Precio típico de casas parecidas/i)).toBeInTheDocument()
    expect(screen.getByText(/6 avisos parecidos/i)).toBeInTheDocument()
    // sin jerga: cohort / stance / pares / mediana peers
    expect(container.textContent).not.toMatch(/cohort|stance|mediana peers/i)
  })

  it('renders nothing when narrative missing', () => {
    const { container } = render(<PriceNarrativeView narrative={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
