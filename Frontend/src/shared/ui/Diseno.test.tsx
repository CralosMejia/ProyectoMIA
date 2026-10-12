import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Boton, EncabezadoPagina, Tarjeta } from './Diseno'

afterEach(() => {
  cleanup()
})

describe('Boton', () => {
  it('renderiza un button con type="button" por defecto', () => {
    render(<Boton>Guardar</Boton>)

    expect(screen.getByRole('button', { name: 'Guardar' })).toHaveAttribute('type', 'button')
  })

  it('respeta type="submit"', () => {
    render(<Boton type="submit">Enviar</Boton>)

    expect(screen.getByRole('button', { name: 'Enviar' })).toHaveAttribute('type', 'submit')
  })

  it('llama a onClick al pulsarlo', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(<Boton onClick={onClick}>Abrir</Boton>)

    await user.click(screen.getByRole('button', { name: 'Abrir' }))

    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('disabled → deshabilitado y no llama a onClick', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    render(
      <Boton disabled onClick={onClick}>
        Abrir
      </Boton>,
    )

    const boton = screen.getByRole('button', { name: 'Abrir' })
    expect(boton).toBeDisabled()
    await user.click(boton)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('pasa los atributos aria-*', () => {
    render(
      <Boton aria-label="Cerrar ventana" aria-expanded="false">
        X
      </Boton>,
    )

    const boton = screen.getByRole('button', { name: 'Cerrar ventana' })
    expect(boton).toHaveAttribute('aria-expanded', 'false')
  })

  it('las tres variantes dan clases distintas y todas con foco visible', () => {
    render(
      <>
        <Boton variante="primario">P</Boton>
        <Boton variante="secundario">S</Boton>
        <Boton variante="peligro">D</Boton>
      </>,
    )

    const clases = ['P', 'S', 'D'].map((n) => screen.getByRole('button', { name: n }).className)
    expect(new Set(clases).size).toBe(3)
    for (const c of clases) {
      expect(c).toMatch(/focus-visible:/)
    }
  })

  it('sin variante → secundario', () => {
    render(
      <>
        <Boton>A</Boton>
        <Boton variante="secundario">B</Boton>
      </>,
    )

    expect(screen.getByRole('button', { name: 'A' }).className).toBe(
      screen.getByRole('button', { name: 'B' }).className,
    )
  })

  it('anade className sin perder las clases base', () => {
    render(<Boton className="self-start">A</Boton>)

    const clases = screen.getByRole('button', { name: 'A' }).className
    expect(clases).toMatch(/\bself-start\b/)
    expect(clases).toMatch(/focus-visible:/)
  })
})

describe('Tarjeta', () => {
  it('con titulo → section con encabezado h2 por defecto', () => {
    const { container } = render(<Tarjeta titulo="Resumen">contenido</Tarjeta>)

    const section = container.querySelector('section')
    expect(section).not.toBeNull()
    expect(screen.getByRole('heading', { level: 2, name: 'Resumen' })).toBeInTheDocument()
    expect(section).toHaveTextContent('contenido')
  })

  it('nivel del titulo configurable', () => {
    render(
      <Tarjeta titulo="Detalle" nivelTitulo={3}>
        x
      </Tarjeta>,
    )

    expect(screen.getByRole('heading', { level: 3, name: 'Detalle' })).toBeInTheDocument()
  })

  it('sin titulo → sin encabezado', () => {
    render(<Tarjeta>solo contenido</Tarjeta>)

    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
    expect(screen.getByText('solo contenido')).toBeInTheDocument()
  })

  it('pasa las props de section (aria-label)', () => {
    render(<Tarjeta aria-label="Filtros">x</Tarjeta>)

    expect(screen.getByRole('region', { name: 'Filtros' })).toBeInTheDocument()
  })
})

describe('EncabezadoPagina', () => {
  it('renderiza un h1 con el titulo', () => {
    render(<EncabezadoPagina titulo="Lista" />)

    expect(screen.getByRole('heading', { level: 1, name: 'Lista' })).toBeInTheDocument()
    expect(screen.getAllByRole('heading')).toHaveLength(1)
  })

  it('subtitulo y acciones opcionales', () => {
    render(
      <EncabezadoPagina
        titulo="Lista"
        subtitulo="Socios ordenados por riesgo"
        acciones={<Boton>Descargar</Boton>}
      />,
    )

    expect(screen.getByText('Socios ordenados por riesgo')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Descargar' })).toBeInTheDocument()
  })

  it('no crea un landmark banner', () => {
    render(<EncabezadoPagina titulo="Lista" />)

    expect(screen.queryByRole('banner')).not.toBeInTheDocument()
  })
})
