import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithQuery } from '../../test/utils'
import PositionForm from '../PositionForm'
import { useSetConfig } from '../../hooks/useSetConfig'

vi.mock('../../hooks/useSetConfig')

const setConfig = {
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  error: null,
}

describe('PositionForm', () => {
  beforeEach(() => {
    setConfig.mutate = vi.fn()
    vi.mocked(useSetConfig).mockReturnValue(setConfig as never)
  })

  it('shows a validation error for out-of-range input and blocks submit', async () => {
    const user = userEvent.setup()
    renderWithQuery(
      <PositionForm cubeStart={[250, 500, 0]} destination={[800, 400, 0]} />,
    )

    const cubeX = screen.getByLabelText('Cube start X')
    await user.clear(cubeX)
    await user.type(cubeX, '5000')

    expect(screen.getByText(/Must be -1000\.\.1000/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /save positions/i }))
    expect(setConfig.mutate).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /save positions/i })).toBeDisabled()
  })

  it('submits a valid config payload', async () => {
    const user = userEvent.setup()
    renderWithQuery(
      <PositionForm cubeStart={[250, 500, 0]} destination={[800, 400, 0]} />,
    )

    const cubeX = screen.getByLabelText('Cube start X')
    await user.clear(cubeX)
    await user.type(cubeX, '300')

    await user.click(screen.getByRole('button', { name: /save positions/i }))

    expect(setConfig.mutate).toHaveBeenCalledTimes(1)
    const [payload] = setConfig.mutate.mock.calls[0]
    expect(payload).toEqual({
      cubeStart: [300, 500, 0],
      destination: [800, 400, 0],
    })
  })
})
