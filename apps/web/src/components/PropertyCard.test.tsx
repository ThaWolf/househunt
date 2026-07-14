import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { PropertyCard } from '@/components/PropertyCard'
import type { SearchResultItem } from '@/api/types'

const sample: SearchResultItem = {
  id: '11111111-1111-1111-1111-111111111111',
  portal: 'zonaprop',
  externalId: 'zp-1',
  sourceUrl: 'https://example.com/listing/1',
  title: 'Casa en Vicente López',
  description: null,
  operation: 'buy',
  propertyType: 'house',
  price: { amount: 250000, currency: 'USD', period: null },
  address: {
    raw: 'Vicente López',
    province: 'Buenos Aires',
    locality: 'Vicente López',
    neighborhood: null,
  },
  rooms: 4,
  bathrooms: 2,
  parking: 1,
  images: [
    {
      url: 'https://cdn.example.com/listing/real-photo.jpg',
      order: 0,
      kind: 'source',
    },
  ],
  descriptionExcerpt: 'Casa luminosa con jardín.',
  listedAt: null,
  scrapedAt: new Date().toISOString(),
  appScore: 72,
  interest: { state: 'active', commentFlag: false },
}

describe('PropertyCard', () => {
  it('shows title, AppScore, interest badge and real image url', () => {
    render(
      <MemoryRouter>
        <PropertyCard item={sample} />
      </MemoryRouter>,
    )
    expect(screen.getByText('Casa en Vicente López')).toBeInTheDocument()
    expect(screen.getByText('72')).toBeInTheDocument()
    expect(screen.getByText(/en interés/i)).toBeInTheDocument()
    expect(screen.getByText(/Casa luminosa/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Ver en portal/i })).toHaveAttribute(
      'href',
      sample.sourceUrl,
    )
    const img = document.querySelector('img')
    expect(img).toHaveAttribute(
      'src',
      'https://cdn.example.com/listing/real-photo.jpg',
    )
  })

  it('skips placeholder kind when a real image exists', () => {
    const withPlaceholder: typeof sample = {
      ...sample,
      images: [
        { url: 'https://example.com/ph.svg', order: 0, kind: 'placeholder' },
        {
          url: 'https://cdn.example.com/real.jpg',
          order: 1,
          kind: 'source',
        },
      ],
    }
    render(
      <MemoryRouter>
        <PropertyCard item={withPlaceholder} />
      </MemoryRouter>,
    )
    expect(document.querySelector('img')).toHaveAttribute(
      'src',
      'https://cdn.example.com/real.jpg',
    )
  })
})
