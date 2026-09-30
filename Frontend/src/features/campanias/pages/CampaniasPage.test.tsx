import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { server } from '../../../mocks/server'
import { reiniciarCampaniasSimuladas } from '../api/campanias-api.handlers'
import CampaniasPage from './CampaniasPage'
import pageSource from './CampaniasPage.tsx?raw'
import formularioSource from '../components/FormularioCampania.tsx?raw'
import tablaSource from '../components/TablaCampanias.tsx?raw'

const CAMPANIAS_PATH = '*/api/v1/campanias'
const EJEMPLO_1 = 'Ejemplo: Llamada personal antes del vencimiento'
const EJEMPLO_2 = 'Ejemplo: Renovación anticipada'

async function renderPagina() {
  const user = userEvent.setup()
  render(<CampaniasPage />)
  const tabla = await screen.findByRole('table', { name: 'Campañas de retención' })
  return { user, tabla }
}

function fila(tabla: HTMLElement, nombre: string): HTMLElement {
  const celda = within(tabla).getByText(nombre)
  const tr = celda.closest('tr')
  if (!tr) throw new Error(`sin fila para ${nombre}`)
  return tr
}

/** Cuenta las escrituras (POST/PUT) a campañas sin cambiar la respuesta por defecto. */
function contarEscrituras() {
  const contador = { llamadas: 0 }
  const contar = () => {
    contador.llamadas += 1
    return undefined
  }
  server.use(http.post(CAMPANIAS_PATH, contar), http.put(`${CAMPANIAS_PATH}/:id`, contar))
  return contador
}

describe('CampaniasPage', () => {
  beforeEach(() => {
    reiniciarCampaniasSimuladas()
  })

  afterEach(() => {
    cleanup()
  })

  it('muestra las columnas, "Activa" y la etiqueta "Ejemplo"; sin botón "Eliminar"', async () => {
    const { tabla } = await renderPagina()

    const encabezados = within(tabla)
      .getAllByRole('columnheader')
      .map((th) => th.textContent)
    expect(encabezados).toEqual([
      'Nombre',
      'Descripción',
      'Niveles',
      'Planes',
      'Prioridad',
      'Estado',
      'Acciones',
    ])
    const primera = fila(tabla, EJEMPLO_2)
    expect(within(primera).getByText('Ejemplo')).toBeInTheDocument()
    expect(within(primera).getByText('Alto, Medio')).toBeInTheDocument()
    expect(within(primera).getByText('Mensual, Trimestral')).toBeInTheDocument()
    expect(within(primera).getByText('Activa')).toBeInTheDocument()
    expect(within(tabla).getAllByText('Ejemplo')).toHaveLength(3)
    expect(screen.queryByRole('button', { name: /eliminar/i })).not.toBeInTheDocument()
  })

  it('"Nueva campaña" abre el formulario con sus campos etiquetados (sin Diario)', async () => {
    const { user } = await renderPagina()

    await user.click(screen.getByRole('button', { name: 'Nueva campaña' }))

    const dialogo = screen.getByRole('dialog', { name: 'Nueva campaña' })
    expect(within(dialogo).getByLabelText('Nombre')).toHaveValue('')
    expect(within(dialogo).getByLabelText('Descripción')).toBeInTheDocument()
    const niveles = within(dialogo).getByRole('group', { name: 'Niveles de riesgo' })
    for (const n of ['Alto', 'Medio', 'Bajo']) {
      expect(within(niveles).getByRole('checkbox', { name: n })).not.toBeChecked()
    }
    const planes = within(dialogo).getByRole('group', { name: 'Planes' })
    expect(within(planes).getAllByRole('checkbox').map((c) => c.closest('label')?.textContent)).toEqual([
      'Mensual',
      'Trimestral',
      'Semestral',
      'Anual',
      'Otro',
    ])
    expect(within(planes).queryByRole('checkbox', { name: 'Diario' })).not.toBeInTheDocument()
    expect(within(dialogo).getByLabelText('Prioridad')).toBeInTheDocument()
  })

  it('guardar vacío → los cuatro mensajes y sin llamar a la API', async () => {
    const { user } = await renderPagina()
    const contador = contarEscrituras()

    await user.click(screen.getByRole('button', { name: 'Nueva campaña' }))
    const dialogo = screen.getByRole('dialog', { name: 'Nueva campaña' })
    await user.type(within(dialogo).getByLabelText('Nombre'), '   ')
    await user.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    expect(within(dialogo).getByText('Escriba un nombre para la campaña.')).toBeInTheDocument()
    expect(within(dialogo).getByText('Elija al menos un nivel de riesgo.')).toBeInTheDocument()
    expect(within(dialogo).getByText('Elija al menos un plan.')).toBeInTheDocument()
    expect(
      within(dialogo).getByText('La prioridad debe ser un número entre 1 y 999.'),
    ).toBeInTheDocument()
    expect(contador.llamadas).toBe(0)
  })

  it.each(['0', '1000'])('prioridad %s → mensaje de rango y sin llamar a la API', async (valor) => {
    const { user } = await renderPagina()
    const contador = contarEscrituras()

    await user.click(screen.getByRole('button', { name: 'Nueva campaña' }))
    const dialogo = screen.getByRole('dialog', { name: 'Nueva campaña' })
    await user.type(within(dialogo).getByLabelText('Nombre'), 'Campaña de prueba')
    await user.click(within(dialogo).getByRole('checkbox', { name: 'Alto' }))
    await user.click(within(dialogo).getByRole('checkbox', { name: 'Mensual' }))
    await user.type(within(dialogo).getByLabelText('Prioridad'), valor)
    await user.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    expect(
      within(dialogo).getByText('La prioridad debe ser un número entre 1 y 999.'),
    ).toBeInTheDocument()
    expect(within(dialogo).queryByText('Escriba un nombre para la campaña.')).not.toBeInTheDocument()
    expect(contador.llamadas).toBe(0)
  })

  it('alta válida → envía el POST y la campaña aparece en la tabla', async () => {
    const { user } = await renderPagina()
    let body: unknown = null
    server.use(
      http.post(CAMPANIAS_PATH, async ({ request }) => {
        body = await request.clone().json()
        return undefined
      }),
    )

    await user.click(screen.getByRole('button', { name: 'Nueva campaña' }))
    const dialogo = screen.getByRole('dialog', { name: 'Nueva campaña' })
    await user.type(within(dialogo).getByLabelText('Nombre'), '  Clase de regalo  ')
    await user.type(within(dialogo).getByLabelText('Descripción'), 'Una clase al renovar.')
    await user.click(within(dialogo).getByRole('checkbox', { name: 'Bajo' }))
    await user.click(within(dialogo).getByRole('checkbox', { name: 'Alto' }))
    await user.click(within(dialogo).getByRole('checkbox', { name: 'Anual' }))
    await user.type(within(dialogo).getByLabelText('Prioridad'), '4')
    await user.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    const tabla = screen.getByRole('table', { name: 'Campañas de retención' })
    const nueva = await within(tabla).findByText('Clase de regalo')
    const tr = nueva.closest('tr') as HTMLElement
    expect(within(tr).queryByText('Ejemplo')).not.toBeInTheDocument()
    expect(within(tr).getByText('Alto, Bajo')).toBeInTheDocument()
    expect(body).toEqual({
      nombre: 'Clase de regalo',
      descripcion: 'Una clase al renovar.',
      niveles_riesgo: ['ALTO', 'BAJO'],
      planes: ['ANUAL'],
      prioridad: 4,
    })
  })

  it('"Editar" precarga los datos y guarda con PUT', async () => {
    const { user, tabla } = await renderPagina()
    let metodo = ''
    server.use(
      http.put(`${CAMPANIAS_PATH}/2`, ({ request }) => {
        metodo = request.method
        return undefined
      }),
    )

    await user.click(within(tabla).getByRole('button', { name: `Editar ${EJEMPLO_2}` }))
    const dialogo = screen.getByRole('dialog', { name: 'Editar campaña' })
    const nombre = within(dialogo).getByLabelText('Nombre')
    expect(nombre).toHaveValue(EJEMPLO_2)
    expect(within(dialogo).getByLabelText('Prioridad')).toHaveValue(2)
    expect(within(dialogo).getByRole('checkbox', { name: 'Alto' })).toBeChecked()
    expect(within(dialogo).getByRole('checkbox', { name: 'Medio' })).toBeChecked()
    expect(within(dialogo).getByRole('checkbox', { name: 'Bajo' })).not.toBeChecked()
    expect(within(dialogo).getByRole('checkbox', { name: 'Trimestral' })).toBeChecked()

    await user.clear(nombre)
    await user.type(nombre, 'Renovación con beneficio')
    await user.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(metodo).toBe('PUT')
    expect(
      await within(screen.getByRole('table')).findByText('Renovación con beneficio'),
    ).toBeInTheDocument()
  })

  it('"Inactivar" pide confirmación; al confirmar pasa a "Inactiva" y el botón desaparece', async () => {
    const { user, tabla } = await renderPagina()

    await user.click(within(tabla).getByRole('button', { name: `Inactivar ${EJEMPLO_1}` }))
    const dialogo = screen.getByRole('dialog', { name: 'Inactivar campaña' })
    expect(
      within(dialogo).getByText(
        /La campaña dejará de sugerirse; las gestiones que ya la usan la conservan\./,
      ),
    ).toBeInTheDocument()
    await user.click(within(dialogo).getByRole('button', { name: 'Inactivar' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    const tr = fila(screen.getByRole('table'), EJEMPLO_1)
    expect(within(tr).getByText('Inactiva')).toBeInTheDocument()
    expect(within(tr).queryByRole('button', { name: /Inactivar/ })).not.toBeInTheDocument()
    expect(within(tr).getByRole('button', { name: `Editar ${EJEMPLO_1}` })).toBeInTheDocument()
  })

  it('cancelar la confirmación no inactiva', async () => {
    const { user, tabla } = await renderPagina()
    const contador = { llamadas: 0 }
    server.use(
      http.post(`${CAMPANIAS_PATH}/:id/inactivar`, () => {
        contador.llamadas += 1
        return undefined
      }),
    )

    await user.click(within(tabla).getByRole('button', { name: `Inactivar ${EJEMPLO_1}` }))
    await user.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancelar' }),
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(contador.llamadas).toBe(0)
    expect(within(fila(tabla, EJEMPLO_1)).getByText('Activa')).toBeInTheDocument()
  })

  it('error del servidor al guardar → ErrorAlert con el mensaje y el formulario sigue abierto', async () => {
    const { user } = await renderPagina()
    server.use(
      http.post(CAMPANIAS_PATH, () =>
        HttpResponse.json(
          { error: { code: 'validation_error', message: 'Mensaje del servidor simulado.' } },
          { status: 400 },
        ),
      ),
    )

    await user.click(screen.getByRole('button', { name: 'Nueva campaña' }))
    const dialogo = screen.getByRole('dialog', { name: 'Nueva campaña' })
    await user.type(within(dialogo).getByLabelText('Nombre'), 'Campaña de prueba')
    await user.click(within(dialogo).getByRole('checkbox', { name: 'Medio' }))
    await user.click(within(dialogo).getByRole('checkbox', { name: 'Otro' }))
    await user.type(within(dialogo).getByLabelText('Prioridad'), '7')
    await user.click(within(dialogo).getByRole('button', { name: 'Guardar' }))

    expect(await within(dialogo).findByRole('alert')).toHaveTextContent(
      'Mensaje del servidor simulado.',
    )
    expect(screen.getByRole('dialog', { name: 'Nueva campaña' })).toBeInTheDocument()
  })

  it('error al inactivar → ErrorAlert con el mensaje en la confirmación', async () => {
    const { user, tabla } = await renderPagina()
    server.use(
      http.post(`${CAMPANIAS_PATH}/:id/inactivar`, () =>
        HttpResponse.json(
          { error: { code: 'not_found', message: 'La campana no existe.' } },
          { status: 404 },
        ),
      ),
    )

    await user.click(within(tabla).getByRole('button', { name: `Inactivar ${EJEMPLO_1}` }))
    const dialogo = screen.getByRole('dialog', { name: 'Inactivar campaña' })
    await user.click(within(dialogo).getByRole('button', { name: 'Inactivar' }))

    expect(await within(dialogo).findByRole('alert')).toHaveTextContent('La campana no existe.')
  })

  it('error al cargar → ErrorAlert con reintento', async () => {
    server.use(
      http.get(
        CAMPANIAS_PATH,
        () =>
          HttpResponse.json(
            { error: { code: 'internal_error', message: 'Falla simulada.' } },
            { status: 500 },
          ),
        { once: true },
      ),
    )
    const user = userEvent.setup()
    render(<CampaniasPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Falla simulada.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByRole('table', { name: 'Campañas de retención' })).toBeInTheDocument()
  })

  it('capas: la página no llama a api/ y los componentes no usan hooks de datos ni api/', () => {
    expect(pageSource).not.toMatch(/from ['"]\.\.\/api\//)
    expect(pageSource).not.toMatch(/\bfetch\s*\(/)
    for (const source of [formularioSource, tablaSource]) {
      expect(source).not.toMatch(/from ['"]\.\.\/(api|hooks)\//)
      expect(source).not.toMatch(/core\/http/)
    }
  })

  it('sin CSS nuevo: ni estilos en línea ni hojas .css en la página ni en sus componentes', () => {
    for (const source of [pageSource, formularioSource, tablaSource]) {
      expect(source).not.toMatch(/style=\{/)
      expect(source).not.toMatch(/\.css['"]/)
    }
  })
})
