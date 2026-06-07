import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithQuery } from '../../test/utils'
import Controls from '../Controls'
import { useHome } from '../../hooks/useHome'
import { useStart } from '../../hooks/useStart'
import { useStop, useResume, useDiscard } from '../../hooks/useStop'

vi.mock('../../hooks/useHome')
vi.mock('../../hooks/useStart')
vi.mock('../../hooks/useStop')

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
  let stop: ReturnType<typeof mockMutation>
  let resume: ReturnType<typeof mockMutation>
  let discard: ReturnType<typeof mockMutation>

  beforeEach(() => {
    home = mockMutation()
    start = mockMutation()
    stop = mockMutation()
    resume = mockMutation()
    discard = mockMutation()
    vi.mocked(useHome).mockReturnValue(home as never)
    vi.mocked(useStart).mockReturnValue(start as never)
    vi.mocked(useStop).mockReturnValue(stop as never)
    vi.mocked(useResume).mockReturnValue(resume as never)
    vi.mocked(useDiscard).mockReturnValue(discard as never)
  })

  it('renders Home and Start buttons', () => {
    renderWithQuery(
      <Controls state="ready" moving={false} resumable={false} home={[0, 0, 0]} />,
    )
    expect(screen.getByRole('button', { name: /home/i })).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /start sequence/i }),
    ).toBeInTheDocument()
  })

  it('calls the mutations when buttons are clicked while ready', async () => {
    const user = userEvent.setup()
    renderWithQuery(
      <Controls state="ready" moving={false} resumable={false} home={[0, 0, 0]} />,
    )

    await user.click(screen.getByRole('button', { name: /home/i }))
    expect(home.mutate).toHaveBeenCalledTimes(1)

    await user.click(screen.getByRole('button', { name: /start sequence/i }))
    expect(start.mutate).toHaveBeenCalledTimes(1)
  })

  it('disables Start when not in ready state', () => {
    renderWithQuery(
      <Controls state="Seq_movingToCube" moving={true} resumable={false} home={[0, 0, 0]} />,
    )
    expect(screen.getByRole('button', { name: /start sequence/i })).toBeDisabled()
  })

  it('enables Stop and triggers it while a sequence is running', async () => {
    const user = userEvent.setup()
    renderWithQuery(
      <Controls state="Seq_movingToCube" moving={true} resumable={false} home={[0, 0, 0]} />,
    )
    const stopBtn = screen.getByRole('button', { name: /stop/i })
    expect(stopBtn).toBeEnabled()
    await user.click(stopBtn)
    expect(stop.mutate).toHaveBeenCalledTimes(1)
  })

  it('shows Resume and Discard for a resumable stop', async () => {
    const user = userEvent.setup()
    renderWithQuery(
      <Controls state="fault" moving={false} resumable={true} home={[0, 0, 0]} />,
    )
    // Start/Home/Stop are replaced by the stop-recovery controls.
    expect(screen.queryByRole('button', { name: /start sequence/i })).toBeNull()
    await user.click(screen.getByRole('button', { name: /resume/i }))
    expect(resume.mutate).toHaveBeenCalledTimes(1)
    await user.click(screen.getByRole('button', { name: /discard/i }))
    expect(discard.mutate).toHaveBeenCalledTimes(1)
  })

  it('disables Home and Start in a non-resumable fault state', () => {
    renderWithQuery(
      <Controls state="fault" moving={false} resumable={false} home={[0, 0, 0]} />,
    )
    expect(screen.getByRole('button', { name: /home/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /start sequence/i })).toBeDisabled()
  })
})
