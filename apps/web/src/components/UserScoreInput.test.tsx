import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UserScoreInput } from '@/components/UserScoreInput'

describe('UserScoreInput', () => {
  it('accepts numeric values 1–10 and not stars', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<UserScoreInput value={null} onChange={onChange} id="us" />)

    const input = screen.getByLabelText(/UserScore del 1 al 10/i)
    expect(input).toHaveAttribute('type', 'number')
    expect(input).toHaveAttribute('min', '1')
    expect(input).toHaveAttribute('max', '10')

    await user.clear(input)
    await user.type(input, '7')
    expect(onChange).toHaveBeenCalled()
    const last = onChange.mock.calls.at(-1)?.[0]
    expect(last).toBe(7)
  })

  it('clamps values above 10', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<UserScoreInput value={5} onChange={onChange} />)
    const input = screen.getByRole('spinbutton')
    await user.clear(input)
    await user.type(input, '99')
    const last = onChange.mock.calls.at(-1)?.[0]
    expect(last).toBe(10)
  })
})
