import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithQuery } from '../../test/utils'
import Controls from '../Controls'
import { useHome } from '../../hooks/useHome'
import { useStart } from '../../hooks/useStart'

vi.mock('../../hooks/useHome')
vi.mock('../../hooks/useStart')

const mockMutation = () => ({
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  error: null,
})

describe('Controls', () => {
  let home: ReturnType<typeof mockMutation>
  let start: ReturnType<typeof mockMutation>

  beforeEach(() => {
    home = mockMutation()
    start = mockMutation()
    vi.mocked(useHome).mockReturnValue(home as never)
    vi.mocked(useStart).mockReturnValue(start as never)
  })

  it('renders Home and Start buttons', () => {
    renderWithQuery(<Controls state="ready" moving={false} home={[0, 0, 0]} />)
    expect(screen.getByRole('button', { name: /home/i })).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /start sequence/i }),
    ).toBeInTheDocument()
  })

  it('calls the mutations when buttons are clicked while ready', async () => {
    const user = userEvent.setup()
    renderWithQuery(<Controls state="ready" moving={false} home={[0, 0, 0]} />)

    await user.click(screen.getByRole('button', { name: /home/i }))
    expect(home.mutate).toHaveBeenCalledTimes(1)

    await user.click(screen.getByRole('button', { name: /start sequence/i }))
    expect(start.mutate).toHaveBeenCalledTimes(1)
  })

  it('disables Start when not in ready state', () => {
    renderWithQuery(<Controls state="Seq_movingToCube" moving={true} home={[0, 0, 0]} />)
    expect(screen.getByRole('button', { name: /start sequence/i })).toBeDisabled()
  })

  it('disables both buttons in fault state', () => {
    renderWithQuery(<Controls state="fault" moving={false} home={[0, 0, 0]} />)
    expect(screen.getByRole('button', { name: /home/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /start sequence/i })).toBeDisabled()
  })
})
