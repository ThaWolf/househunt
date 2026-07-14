import { describe, expect, it } from 'vitest'
import {
  canOpenPortalCta,
  dataSourceBadgeLabel,
  hasNonLiveResults,
  isStockImageUrl,
  isValidPortalUrl,
  resolveDataSource,
} from '@/lib/listingFidelity'
import { galleryImages, isRealImage, primaryImageUrl } from '@/lib/format'
import type { ImageRef } from '@/api/types'

describe('listingFidelity', () => {
  it('resolveDataSource prefers wire dataSource then alias', () => {
    expect(resolveDataSource({ dataSource: 'live' })).toBe('live')
    expect(
      resolveDataSource({
        dataSource: 'demo_stub',
        listingFidelity: 'live',
      }),
    ).toBe('demo_stub')
    expect(
      resolveDataSource({
        dataSource: undefined as unknown as 'live',
        listingFidelity: 'fixture_curated',
      }),
    ).toBe('fixture_curated')
  })

  it('badge labels only when non-live', () => {
    expect(dataSourceBadgeLabel('live')).toBeNull()
    expect(dataSourceBadgeLabel('fixture_curated')).toBe('Fixtures')
    expect(dataSourceBadgeLabel('demo_stub')).toBe('Demo')
  })

  it('CTA rules E18', () => {
    expect(
      canOpenPortalCta({
        dataSource: 'live',
        sourceUrl: 'https://www.zonaprop.com.ar/x',
      }),
    ).toBe(true)
    expect(
      canOpenPortalCta({
        dataSource: 'demo_stub',
        sourceUrl: 'https://www.zonaprop.com.ar/x',
      }),
    ).toBe(false)
    expect(
      canOpenPortalCta({
        dataSource: 'fixture_curated',
        sourceUrl: 'https://www.zonaprop.com.ar/x',
      }),
    ).toBe(true)
    expect(
      canOpenPortalCta({ dataSource: 'fixture_curated', sourceUrl: '' }),
    ).toBe(false)
    expect(isValidPortalUrl('ftp://x')).toBe(false)
  })

  it('bans stock CDN hosts', () => {
    expect(isStockImageUrl('https://picsum.photos/seed/1/400')).toBe(true)
    expect(isStockImageUrl('https://images.unsplash.com/photo-1')).toBe(true)
    expect(
      isStockImageUrl('https://imganuncios.mitula.net/listing/a.jpg'),
    ).toBe(false)
  })

  it('hasNonLiveResults detects mixed inventory', () => {
    expect(
      hasNonLiveResults([
        { dataSource: 'live' },
        { dataSource: 'fixture_curated' },
      ]),
    ).toBe(true)
    expect(hasNonLiveResults([{ dataSource: 'live' }], 'live')).toBe(false)
    expect(hasNonLiveResults([{ dataSource: 'live' }], 'fixtures')).toBe(true)
  })
})

describe('image honesty', () => {
  it('never treats stock or placeholder as real', () => {
    const stock: ImageRef = {
      url: 'https://picsum.photos/seed/x/800/600',
      order: 0,
      kind: 'source',
    }
    const ph: ImageRef = {
      url: 'https://cdn.portal.com/x.jpg',
      order: 0,
      kind: 'placeholder',
    }
    const real: ImageRef = {
      url: 'https://cdn.portal.com/x.jpg',
      order: 1,
      kind: 'source',
    }
    expect(isRealImage(stock)).toBe(false)
    expect(isRealImage(ph)).toBe(false)
    expect(isRealImage(real)).toBe(true)
    expect(primaryImageUrl([stock, ph])).toBeNull()
    expect(galleryImages([stock, ph, real])).toEqual([real])
  })
})
