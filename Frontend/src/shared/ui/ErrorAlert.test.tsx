import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErrorAlert } from './ErrorAlert'

describe('ErrorAlert', () => {
  afterEach(() => {
    cleanup()
  })

  it('role="alert" con el mensaje', () => {
    render(<ErrorAlert message="No se pudo cargar" />)

    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo cargar')
  })

  it('con onRetry → clic en "Reintentar" lo llama 1 vez', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(<ErrorAlert message="Fallo" onRetry={onRetry} />)

    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('sin onRetry → no hay boton', () => {
    render(<ErrorAlert message="Fallo" />)

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
