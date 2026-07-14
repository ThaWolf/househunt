import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HumanizedReportView } from '@/components/HumanizedReportView'
import type { HumanizedReport } from '@/api/types'

const sample: HumanizedReport = {
  summary: 'Casa sólida con buen ajuste de precio.',
  appScore: 72,
  components: [
    {
      id: 'attrs',
      label: 'Atributos',
      helpText:
        'Habitaciones, baños, cochera y amenities vs lo esperado para una casa.',
      score: 80,
      maxScore: 100,
      barPct: 80,
    },
    {
      id: 'area',
      label: 'Superficie',
      helpText:
        'Metros cubiertos y terreno frente a un rango típico del cohort local.',
      score: 60,
      maxScore: 100,
      barPct: 60,
    },
    {
      id: 'zone',
      label: 'Zona',
      helpText: 'Actividad del entorno (POI, comercios, transporte) cerca del inmueble.',
      score: 50,
      maxScore: 100,
      barPct: 50,
      summary: 'Sin datos de zona — peso redistribuido',
    },
    {
      id: 'priceFit',
      label: 'Ajuste de precio',
      helpText:
        'Qué tan alineado está el precio vs casas similares (mismo band de zona).',
      score: 70,
      maxScore: 100,
      barPct: 70,
    },
    {
      id: 'riskSafety',
      label: 'Salud legal / riesgo',
      helpText:
        'Señales en el texto del aviso (obra, legal, patología). 100 = sin señales; 0 = muchas.',
      score: 90,
      maxScore: 100,
      barPct: 90,
    },
  ],
  riskHits: [{ keyword: 'a refaccionar', weight: 0.4, label: 'Riesgo de obra' }],
  generatedAt: '2026-07-14T12:00:00.000Z',
}

describe('HumanizedReportView', () => {
  it('renders helpText, riskSafety label, and bars without raw JSON', () => {
    const { container } = render(<HumanizedReportView report={sample} />)
    expect(screen.getByText('Reporte Househunt')).toBeInTheDocument()
    expect(screen.getByText(/Casa sólida/)).toBeInTheDocument()
    expect(screen.getByText('Atributos')).toBeInTheDocument()
    expect(screen.getByText('Superficie')).toBeInTheDocument()
    expect(screen.getByText('Zona')).toBeInTheDocument()
    expect(screen.getByText('Ajuste de precio')).toBeInTheDocument()
    expect(screen.getByText('Salud legal / riesgo')).toBeInTheDocument()
    expect(
      screen.getByText(/100 = sin señales/i),
    ).toBeInTheDocument()
    expect(screen.getByText('Riesgo de obra')).toBeInTheDocument()
    expect(screen.getByLabelText('Atributos')).toHaveAttribute(
      'aria-valuenow',
      '80',
    )
    expect(container.querySelector('pre')).toBeNull()
    expect(container.textContent).not.toMatch(/"weights"/)
  })

  it('maps legacy risk id to Salud legal / riesgo and clean subtitle', () => {
    const legacy: HumanizedReport = {
      summary: null,
      appScore: 88,
      components: [
        {
          id: 'risk',
          label: 'Riesgo',
          helpText: '',
          score: 100,
          maxScore: 100,
          barPct: 100,
        },
      ],
      riskHits: [],
      generatedAt: '2026-07-14T12:00:00.000Z',
    }
    render(<HumanizedReportView report={legacy} />)
    expect(screen.getByText('Salud legal / riesgo')).toBeInTheDocument()
    expect(screen.getByText(/Sin señales de riesgo en el aviso/i)).toBeInTheDocument()
    expect(screen.queryByText(/^Riesgo$/)).not.toBeInTheDocument()
  })

  it('shows empty state when report is null', () => {
    render(<HumanizedReportView report={null} fallbackAppScore={40} />)
    expect(screen.getByText(/aún no generado/i)).toBeInTheDocument()
  })
})
