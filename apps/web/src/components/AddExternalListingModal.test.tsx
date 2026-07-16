import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AddExternalListingModal } from '@/components/AddExternalListingModal'
import { ApiError } from '@/api/client'
import { interestApi } from '@/api/endpoints'
import type { InterestItem } from '@/api/types'

vi.mock('@/api/endpoints', () => ({
  interestApi: {
    createExternal: vi.fn(),
  },
}))

vi.mock('@/context/ActiveListContext', () => ({
  useActiveList: () => ({
    activeListId: 'list-1',
    activeList: { id: 'list-1', name: 'Mi lista', role: 'owner', memberCount: 1 },
    lists: [],
    loading: false,
    error: null,
    setActiveListId: vi.fn(),
    refreshLists: vi.fn(),
  }),
}))

const mockCreate = vi.mocked(interestApi.createExternal)

function fakeItem(): InterestItem {
  return {
    id: 'i1',
    property: {
      id: 'p1',
      sourceUrl: 'https://example.com/casa',
      dataSource: 'external',
      title: 'Casa externa',
    },
    state: 'active',
  } as unknown as InterestItem
}

describe('AddExternalListingModal', () => {
  it('disables submit until URL is valid, then creates and closes', async () => {
    const user = userEvent.setup()
    mockCreate.mockResolvedValueOnce(fakeItem())
    const onAdded = vi.fn()
    const onClose = vi.fn()

    render(<AddExternalListingModal onClose={onClose} onAdded={onAdded} />)

    const submit = screen.getByRole('button', { name: /Agregar$/i })
    expect(submit).toBeDisabled()

    await user.type(
      screen.getByLabelText(/URL de la publicación/i),
      'https://example.com/casa',
    )
    expect(submit).toBeEnabled()

    await user.click(submit)

    await waitFor(() => expect(mockCreate).toHaveBeenCalledWith({
      url: 'https://example.com/casa',
      listId: 'list-1',
    }))
    expect(onAdded).toHaveBeenCalledTimes(1)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('shows a friendly message when the listing is already saved (409)', async () => {
    const user = userEvent.setup()
    mockCreate.mockRejectedValueOnce(
      new ApiError(409, { code: 'interest_exists', message: 'dup', details: null }),
    )

    render(<AddExternalListingModal onClose={vi.fn()} onAdded={vi.fn()} />)

    await user.type(
      screen.getByLabelText(/URL de la publicación/i),
      'https://example.com/casa',
    )
    await user.click(screen.getByRole('button', { name: /Agregar$/i }))

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(/ya está en tus intereses/i),
    )
  })
})
