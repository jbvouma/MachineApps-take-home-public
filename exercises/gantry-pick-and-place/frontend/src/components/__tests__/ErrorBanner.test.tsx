import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithQuery } from '../../test/utils'
import ErrorBanner from '../ErrorBanner'
import { useReset } from '../../hooks/useReset'

vi.mock('../../hooks/useReset')

const reset = {
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  error: null,
}

describe('ErrorBanner', () => {
  beforeEach(() => {
    reset.mutate = vi.fn()
    vi.mocked(useReset).mockReturnValue(reset as never)
  })

  it('renders nothing when state is ready and no errors', () => {
    const { container } = renderWithQuery(<ErrorBanner state="ready" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows on fault and Reset triggers the reset mutation', async () => {
    const user = userEvent.setup()
    renderWithQuery(
      <ErrorBanner state="fault" errorMessage="Gripper jammed" />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent(/Gripper jammed/)

    await user.click(screen.getByRole('button', { name: /reset fault/i }))
    expect(reset.mutate).toHaveBeenCalledTimes(1)
  })

  it('surfaces a network/RPC error without a reset button', () => {
    renderWithQuery(
      <ErrorBanner state="ready" extraError="Network unreachable" />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/Network unreachable/)
    expect(
      screen.queryByRole('button', { name: /reset fault/i }),
    ).not.toBeInTheDocument()
  })
})
