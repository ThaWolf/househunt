import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { PropertyCard } from '@/components/PropertyCard'
import type { SearchResultItem } from '@/api/types'

const sample: SearchResultItem = {
  id: '11111111-1111-1111-1111-111111111111',
  portal: 'zonaprop',
  externalId: 'zp-1',
  sourceUrl: 'https://www.zonaprop.com.ar/propiedades/real-listing.html',
  dataSource: 'live',
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
  it('shows title, AppScore, interest badge and real image url for live', () => {
    render(
      <MemoryRouter>
        <PropertyCard item={sample} />
      </MemoryRouter>,
    )
    expect(screen.getByText('Casa en Vicente López')).toBeInTheDocument()
    expect(screen.getByText('72')).toBeInTheDocument()
    expect(screen.getByText(/en interés/i)).toBeInTheDocument()
    expect(screen.getByText(/Casa luminosa/)).toBeInTheDocument()
    expect(screen.queryByTestId('data-source-badge')).not.toBeInTheDocument()
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

  it('shows Fixtures badge and portal CTA for fixture_curated with valid URL', () => {
    render(
      <MemoryRouter>
        <PropertyCard
          item={{ ...sample, dataSource: 'fixture_curated', interest: null }}
        />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('data-source-badge')).toHaveTextContent('Fixtures')
    expect(screen.getByRole('link', { name: /Ver en portal/i })).toBeInTheDocument()
  })

  it('shows Demo badge and disables portal CTA for demo_stub', () => {
    render(
      <MemoryRouter>
        <PropertyCard
          item={{
            ...sample,
            dataSource: 'demo_stub',
            sourceUrl: 'https://www.zonaprop.com.ar/propiedades/fake.html',
            interest: null,
          }}
        />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('data-source-badge')).toHaveTextContent('Demo')
    expect(screen.queryByRole('link', { name: /Ver en portal/i })).not.toBeInTheDocument()
    expect(screen.getByTestId('portal-cta-disabled')).toHaveTextContent(
      /Sin aviso real \(demo\)/i,
    )
  })

  it('hides portal CTA when fixture URL is invalid', () => {
    render(
      <MemoryRouter>
        <PropertyCard
          item={{
            ...sample,
            dataSource: 'fixture_curated',
            sourceUrl: 'not-a-url',
            interest: null,
          }}
        />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('link', { name: /Ver en portal/i })).not.toBeInTheDocument()
    expect(screen.getByTestId('portal-cta-disabled')).toHaveTextContent(
      /Portal no disponible/i,
    )
  })

  it('renders Househunt placeholder instead of stock picsum as source', () => {
    render(
      <MemoryRouter>
        <PropertyCard
          item={{
            ...sample,
            interest: null,
            images: [
              {
                url: 'https://picsum.photos/seed/zp-1/800/600',
                order: 0,
                kind: 'source',
              },
            ],
          }}
        />
      </MemoryRouter>,
    )
    expect(document.querySelector('img')).toBeNull()
    expect(screen.getByTestId('househunt-placeholder')).toBeInTheDocument()
  })

  it('renders Househunt placeholder for kind=placeholder only', () => {
    render(
      <MemoryRouter>
        <PropertyCard
          item={{
            ...sample,
            interest: null,
            images: [
              {
                url: 'https://cdn.example.com/ignored.svg',
                order: 0,
                kind: 'placeholder',
              },
            ],
          }}
        />
      </MemoryRouter>,
    )
    expect(document.querySelector('img')).toBeNull()
    expect(screen.getByTestId('househunt-placeholder')).toBeInTheDocument()
  })
})
