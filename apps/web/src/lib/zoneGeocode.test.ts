import { describe, expect, it } from 'vitest'
import { isWeakGeocode } from '@/lib/zoneGeocode'

describe('isWeakGeocode', () => {
  it('treats missing zone and map as weak', () => {
    expect(isWeakGeocode(null, null)).toBe(true)
  })

  it('treats approximate and missing statuses as weak', () => {
    expect(
      isWeakGeocode(
        {
          poi: [],
          commerce: [],
          transit: [],
          geo: { geocodeStatus: 'approximate' },
          generatedAt: '2026-07-14T12:00:00.000Z',
          provider: 'seed',
        },
        null,
      ),
    ).toBe(true)
    expect(
      isWeakGeocode(
        {
          poi: [],
          commerce: [],
          transit: [],
          geo: { geocodeStatus: 'missing' },
          generatedAt: '2026-07-14T12:00:00.000Z',
          provider: 'seed',
        },
        null,
      ),
    ).toBe(true)
  })

  it('treats exact geocode as strong', () => {
    expect(
      isWeakGeocode(
        {
          poi: [],
          commerce: [],
          transit: [],
          geo: { geocodeStatus: 'exact', lat: -34.8, lng: -58.0 },
          generatedAt: '2026-07-14T12:00:00.000Z',
          provider: 'seed',
        },
        {
          center: { lat: -34.8, lng: -58.0 },
          pins: [],
          externalUrl: 'https://maps.google.com',
          provider: 'google_embed',
          embedUrl: 'https://www.google.com/maps/embed?pb=test',
        },
      ),
    ).toBe(false)
  })
})
