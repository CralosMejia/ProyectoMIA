import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { useEffect, useState } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
import { server } from '../../mocks/server'
import { reiniciarAccesoDenegado } from '../http/acceso-denegado'
import { httpGet } from '../http/http-client'
import { AppLayout } from './AppLayout'

const ENLACES = [
  { name: 'Inicio', path: '/' },
  { name: 'Carga', path: '/carga' },
  { name: 'Lista', path: '/lista' },
  { name: 'Campañas', path: '/campanias' },
  { name: 'Dashboard', path: '/dashboard' },
]

function renderLayout(initialPath: string) {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { index: true, element: <p>contenido inicio</p> },
          { path: 'carga', element: <p>contenido carga</p> },
          { path: 'lista', element: <p>contenido lista</p> },
          { path: 'campanias', element: <p>contenido campanias</p> },
          { path: 'dashboard', element: <p>contenido dashboard</p> },
        ],
      },
    ],
    { initialEntries: [initialPath] },
  )
  render(<RouterProvider router={router} />)
  return router
}

describe('AppLayout', () => {
  afterEach(() => {
    cleanup()
  })

  it('renderiza una navegacion con los 5 enlaces esperados', () => {
    renderLayout('/')

    const nav = screen.getByRole('navigation')
    const links = within(nav).getAllByRole('link')
    expect(links.map((l) => l.textContent)).toEqual(ENLACES.map((e) => e.name))
    for (const { name, path } of ENLACES) {
      expect(within(nav).getByRole('link', { name })).toHaveAttribute('href', path)
    }
  })

  it.each(ENLACES)('en $path solo el enlace "$name" tiene aria-current="page"', ({ name, path }) => {
    renderLayout(path)

    const nav = screen.getByRole('navigation')
    for (const link of within(nav).getAllByRole('link')) {
      if (link.textContent === name) {
        expect(link).toHaveAttribute('aria-current', 'page')
      } else {
        expect(link).not.toHaveAttribute('aria-current')
      }
    }
  })

  it('clic en "Campañas" → la URL pasa a /campanias y el main muestra su contenido', async () => {
    const user = userEvent.setup()
    const router = renderLayout('/')
    expect(within(screen.getByRole('main')).getByText('contenido inicio')).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: 'Campañas' }))

    expect(router.state.location.pathname).toBe('/campanias')
    const main = screen.getByRole('main')
    expect(within(main).getByText('contenido campanias')).toBeInTheDocument()
    expect(within(main).queryByText('contenido inicio')).not.toBeInTheDocument()
  })

  it('tiene un header con la navegacion fuera del main', () => {
    renderLayout('/')

    const header = screen.getByRole('banner')
    expect(within(header).getByRole('navigation')).toBeInTheDocument()
    expect(within(screen.getByRole('main')).queryByRole('navigation')).not.toBeInTheDocument()
  })
})

/** Pagina de prueba que consulta el estado del sistema al montarse, como Inicio. */
function PaginaQueConsulta() {
  const [texto, setTexto] = useState('consultando')
  useEffect(() => {
    httpGet('/api/v1/sistema/estado').then(
      () => setTexto('estado recibido'),
      () => setTexto('fallo la consulta'),
    )
  }, [])
  return <p>{texto}</p>
}

function renderConConsulta() {
  const router = createMemoryRouter(
    [{ path: '/', element: <AppLayout />, children: [{ index: true, element: <PaginaQueConsulta /> }] }],
    { initialEntries: ['/'] },
  )
  render(<RouterProvider router={router} />)
}

describe('AppLayout: acceso no permitido (CU-00)', () => {
  afterEach(() => {
    cleanup()
    reiniciarAccesoDenegado()
  })

  it('403 forbidden en /sistema/estado → solo el aviso, sin navegacion ni codigos', async () => {
    server.use(
      http.get('*/api/v1/sistema/estado', () =>
        HttpResponse.json(
          { error: { code: 'forbidden', message: 'El acceso no esta permitido desde este equipo.' } },
          { status: 403 },
        ),
      ),
    )

    renderConConsulta()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Acceso no permitido' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        'Este equipo no está autorizado para usar la aplicación. Pida al responsable técnico que lo añada a la lista de equipos permitidos.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
    expect(screen.queryAllByRole('link')).toHaveLength(0)
    expect(screen.queryByText(/consultando|fallo la consulta/)).not.toBeInTheDocument()
    const texto = document.body.textContent ?? ''
    expect(texto).not.toMatch(/403|forbidden/i)
  })

  it('sin 403 → layout normal con la navegacion y el contenido', async () => {
    renderConConsulta()

    expect(await screen.findByText('estado recibido')).toBeInTheDocument()
    expect(screen.getByRole('navigation')).toBeInTheDocument()
    expect(screen.queryByText('Acceso no permitido')).not.toBeInTheDocument()
  })

  it('otro error (500) no muestra el aviso', async () => {
    server.use(
      http.get('*/api/v1/sistema/estado', () =>
        HttpResponse.json(
          { error: { code: 'internal_error', message: 'Error interno del servidor.' } },
          { status: 500 },
        ),
      ),
    )

    renderConConsulta()

    expect(await screen.findByText('fallo la consulta')).toBeInTheDocument()
    expect(screen.getByRole('navigation')).toBeInTheDocument()
    expect(screen.queryByText('Acceso no permitido')).not.toBeInTheDocument()
  })
})
