import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { LoadingIndicator } from './LoadingIndicator'

describe('LoadingIndicator', () => {
  afterEach(() => {
    cleanup()
  })

  it('role="status" con el texto recibido', () => {
    render(<LoadingIndicator label="Cargando socios..." />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando socios...')
  })

  it('sin label → texto por defecto accesible', () => {
    render(<LoadingIndicator />)

    expect(screen.getByRole('status')).toHaveTextContent('Cargando...')
  })
})
