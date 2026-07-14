import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DescriptionBlock } from '@/components/DescriptionBlock'

describe('DescriptionBlock', () => {
  it('expands and collapses long description', async () => {
    const user = userEvent.setup()
    const long = 'A'.repeat(500)
    render(<DescriptionBlock description={long} collapseAt={100} />)
    expect(screen.getByText(/Ver descripción completa/i)).toBeInTheDocument()
    await user.click(screen.getByText(/Ver descripción completa/i))
    expect(screen.getByText(/Ver menos/i)).toBeInTheDocument()
    expect(screen.getByText(long)).toBeInTheDocument()
  })

  it('falls back to excerpt with hint when no full description', () => {
    render(
      <DescriptionBlock description={null} excerpt="Teaser corto del aviso." />,
    )
    expect(screen.getByText(/Teaser corto/)).toBeInTheDocument()
    expect(screen.getByText(/Solo excerpt/i)).toBeInTheDocument()
  })
})
