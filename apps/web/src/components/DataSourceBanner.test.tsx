import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DataSourceBanner } from '@/components/DataSourceBanner'
import type { SearchResultItem } from '@/api/types'

const base: SearchResultItem = {
  id: '11111111-1111-1111-1111-111111111111',
  portal: 'zonaprop',
  externalId: '1',
  sourceUrl: 'https://example.com/a',
  dataSource: 'live',
  title: 'A',
  description: null,
  operation: 'buy',
  propertyType: 'house',
  rooms: 3,
  bathrooms: 1,
  parking: 0,
  images: [],
  listedAt: null,
  scrapedAt: new Date().toISOString(),
  appScore: 50,
}

describe('DataSourceBanner', () => {
  it('hides when all live', () => {
    const { container } = render(
      <DataSourceBanner items={[base]} density={{ mode: 'live' }} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('shows when any non-live item', () => {
    render(
      <DataSourceBanner
        items={[{ ...base, dataSource: 'demo_stub' }]}
        density={{ mode: 'fixtures', dataSourceHint: 'demo_stub' }}
      />,
    )
    expect(screen.getByTestId('data-source-banner')).toBeInTheDocument()
    expect(screen.getByText(/Origen mixto/i)).toBeInTheDocument()
  })
})
