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
        'Habitaciones, baños, cochera y comodidades, comparado con lo esperable para una casa.',
      score: 80,
      maxScore: 100,
      barPct: 80,
    },
    {
      id: 'area',
      label: 'Superficie',
      helpText:
        'Metros cubiertos y de terreno, comparado con casas parecidas de la zona.',
      score: 60,
      maxScore: 100,
      barPct: 60,
    },
    {
      id: 'zone',
      label: 'Zona',
      helpText:
        'Qué tan movida está la zona: comercios, transporte y lugares cerca del inmueble.',
      score: 50,
      maxScore: 100,
      barPct: 50,
      summary:
        'No pudimos analizar la zona en esta búsqueda, así que este punto no baja el puntaje.',
    },
    {
      id: 'priceFit',
      label: 'Ajuste de precio',
      helpText:
        'Si el precio está barato, caro o en su punto para casas parecidas de la zona.',
      score: 70,
      maxScore: 100,
      barPct: 70,
    },
    {
      id: 'riskSafety',
      label: 'Seguridad',
      helpText:
        'Buscamos alertas en el texto del aviso (para refaccionar, humedad, temas legales). 100 = sin alertas; más bajo = más señales para revisar.',
      score: 90,
      maxScore: 100,
      barPct: 90,
    },
  ],
  riskHits: [{ keyword: 'a refaccionar', weight: 0.4, label: 'Riesgo de obra' }],
  generatedAt: '2026-07-14T12:00:00.000Z',
}

describe('HumanizedReportView', () => {
  it('renders friendly labels, positive Seguridad score, tooltips and bars without raw JSON', () => {
    const { container } = render(<HumanizedReportView report={sample} />)
    expect(screen.getByText('Reporte Househunt')).toBeInTheDocument()
    expect(screen.getByText(/Casa sólida/)).toBeInTheDocument()
    expect(screen.getByText('Atributos')).toBeInTheDocument()
    expect(screen.getByText('Superficie')).toBeInTheDocument()
    expect(screen.getByText('Zona')).toBeInTheDocument()
    expect(screen.getByText('Ajuste de precio')).toBeInTheDocument()
    // Score renombrado en positivo, sin "riesgo" ni "salud legal"
    expect(screen.getByText('Seguridad')).toBeInTheDocument()
    expect(screen.queryByText(/salud legal/i)).not.toBeInTheDocument()
    // helpText vive en el tooltip "?" (fuera del cuerpo), no como párrafo permanente
    expect(
      screen.getByRole('button', { name: /Qué mide Seguridad/i }),
    ).toBeInTheDocument()
    expect(screen.getByText('Riesgo de obra')).toBeInTheDocument()
    expect(screen.getByLabelText('Atributos')).toHaveAttribute(
      'aria-valuenow',
      '80',
    )
    expect(container.querySelector('pre')).toBeNull()
    expect(container.textContent).not.toMatch(/"weights"/)
    // sin jerga técnica en el cuerpo del informe
    expect(container.textContent).not.toMatch(/cohort|peso redistribuido|patología/i)
  })

  it('maps legacy risk id to positive Seguridad label and clean subtitle', () => {
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
    expect(screen.getByText('Seguridad')).toBeInTheDocument()
    expect(screen.getByText(/Sin alertas en el texto del aviso/i)).toBeInTheDocument()
    expect(screen.queryByText(/^Riesgo$/)).not.toBeInTheDocument()
  })

  it('shows empty state when report is null', () => {
    render(<HumanizedReportView report={null} fallbackAppScore={40} />)
    expect(screen.getByText(/aún no generado/i)).toBeInTheDocument()
  })
})
