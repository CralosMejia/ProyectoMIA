import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { HealthStatusCard, type HealthStatusCardProps } from './HealthStatusCard'

function buildProps(overrides: Partial<HealthStatusCardProps> = {}): HealthStatusCardProps {
  return {
    status: 'ok',
    database: 'up',
    checkedAt: new Date('2026-01-01T00:00:00Z'),
    ...overrides,
  }
}

describe('HealthStatusCard', () => {
  afterEach(() => {
    cleanup()
  })

  it('status ok y database up → "Sistema operativo" y "Base de datos: conectada"', () => {
    render(<HealthStatusCard {...buildProps()} />)

    expect(screen.getByRole('heading', { name: 'Sistema operativo' })).toBeInTheDocument()
    expect(screen.getByText('Base de datos: conectada')).toBeInTheDocument()
    expect(screen.queryByText('Servicio degradado')).not.toBeInTheDocument()
  })

  it('status degraded y database down → "Servicio degradado" y "Base de datos: sin conexión"', () => {
    render(<HealthStatusCard {...buildProps({ status: 'degraded', database: 'down' })} />)

    expect(screen.getByRole('heading', { name: 'Servicio degradado' })).toBeInTheDocument()
    expect(screen.getByText('Base de datos: sin conexión')).toBeInTheDocument()
    expect(screen.queryByText('Sistema operativo')).not.toBeInTheDocument()
  })

  it('combinacion mixta degraded/up → cada prop se pinta de forma independiente', () => {
    render(<HealthStatusCard {...buildProps({ status: 'degraded', database: 'up' })} />)

    expect(screen.getByRole('heading', { name: 'Servicio degradado' })).toBeInTheDocument()
    expect(screen.getByText('Base de datos: conectada')).toBeInTheDocument()
  })

  it('checkedAt → elemento time con dateTime ISO de la fecha recibida', () => {
    const { container } = render(<HealthStatusCard {...buildProps()} />)

    const time = container.querySelector('time')
    expect(time).not.toBeNull()
    expect(time).toHaveAttribute('datetime', '2026-01-01T00:00:00.000Z')
  })

  it('renderizado presentacional → no expone indicador de carga ni alerta', () => {
    render(<HealthStatusCard {...buildProps()} />)

    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
