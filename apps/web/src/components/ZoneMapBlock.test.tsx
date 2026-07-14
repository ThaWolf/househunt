import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ZoneMapBlock } from '@/components/ZoneMapBlock'
import type { MapEmbed, ZoneReport } from '@/api/types'

const zone: ZoneReport = {
  summary: 'Entorno residencial con comercios cercanos.',
  poi: [
    {
      id: 'p1',
      name: 'Plaza Rodríguez',
      category: 'plaza',
      distanceM: 400,
      source: 'seed',
    },
  ],
  commerce: [
    {
      id: 'c1',
      name: 'Supermercado Dia',
      category: 'supermercado',
      distanceM: 250,
      source: 'seed',
    },
  ],
  transit: [],
  geo: { geocodeStatus: 'approximate', lat: -34.88, lng: -58.01 },
  generatedAt: '2026-07-14T12:00:00.000Z',
  provider: 'seed',
}

const mapEmbed: MapEmbed = {
  center: { lat: -34.88, lng: -58.01 },
  pins: [
    {
      id: 'listing',
      lat: -34.88,
      lng: -58.01,
      label: 'Propiedad',
      kind: 'listing',
    },
  ],
  embedUrl: 'https://www.google.com/maps/embed?pb=test',
  externalUrl: 'https://maps.google.com/?q=-34.88,-58.01',
  provider: 'google_embed',
}

describe('ZoneMapBlock', () => {
  it('renders zone lists and iframe when embedUrl present', () => {
    render(<ZoneMapBlock zoneReport={zone} map={mapEmbed} />)
    expect(screen.getByText('Plaza Rodríguez')).toBeInTheDocument()
    expect(screen.getByText('Supermercado Dia')).toBeInTheDocument()
    const iframe = screen.getByTitle('Mapa de la propiedad')
    expect(iframe).toHaveAttribute('src', mapEmbed.embedUrl!)
    expect(
      screen.getByRole('link', { name: /Abrir en Google Maps/i }),
    ).toHaveAttribute('href', mapEmbed.externalUrl)
  })

  it('shows CTA only when embedUrl missing', () => {
    const externalOnly: MapEmbed = {
      ...mapEmbed,
      embedUrl: null,
      provider: 'external_only',
    }
    render(<ZoneMapBlock zoneReport={zone} map={externalOnly} />)
    expect(screen.queryByTitle('Mapa de la propiedad')).not.toBeInTheDocument()
    expect(screen.getByText(/Mapa embebido no disponible/i)).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /Abrir en Google Maps/i }),
    ).toBeInTheDocument()
  })
})
