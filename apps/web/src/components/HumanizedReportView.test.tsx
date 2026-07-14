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
      score: 80,
      maxScore: 100,
      barPct: 80,
    },
    {
      id: 'area',
      label: 'Área',
      score: 60,
      maxScore: 100,
      barPct: 60,
    },
    {
      id: 'zone',
      label: 'Zona',
      score: 50,
      maxScore: 100,
      barPct: 50,
      note: 'Sin datos de zona — peso redistribuido',
    },
    {
      id: 'priceFit',
      label: 'Ajuste precio',
      score: 70,
      maxScore: 100,
      barPct: 70,
    },
    {
      id: 'risk',
      label: 'Riesgo',
      score: 90,
      maxScore: 100,
      barPct: 90,
    },
  ],
  riskHits: [{ term: 'a refaccionar', label: 'Riesgo de obra' }],
  generatedAt: '2026-07-14T12:00:00.000Z',
}

describe('HumanizedReportView', () => {
  it('renders labels and bars without raw JSON', () => {
    const { container } = render(<HumanizedReportView report={sample} />)
    expect(screen.getByText('Reporte Househunt')).toBeInTheDocument()
    expect(screen.getByText(/Casa sólida/)).toBeInTheDocument()
    expect(screen.getByText('Atributos')).toBeInTheDocument()
    expect(screen.getByText('Área')).toBeInTheDocument()
    expect(screen.getByText('Zona')).toBeInTheDocument()
    expect(screen.getByText('Ajuste precio')).toBeInTheDocument()
    expect(screen.getByText('Riesgo de obra')).toBeInTheDocument()
    expect(screen.getByLabelText('Atributos')).toHaveAttribute(
      'aria-valuenow',
      '80',
    )
    expect(container.querySelector('pre')).toBeNull()
    expect(container.textContent).not.toMatch(/"weights"/)
  })

  it('shows empty state when report is null', () => {
    render(<HumanizedReportView report={null} fallbackAppScore={40} />)
    expect(screen.getByText(/aún no generado/i)).toBeInTheDocument()
  })
})
