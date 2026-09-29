import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'
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
