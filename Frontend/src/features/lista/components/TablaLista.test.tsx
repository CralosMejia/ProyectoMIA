import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ListaPriorizada, Prediccion } from '../types'
import { TablaLista, TITULO_OTROS, TITULO_PRIORITARIOS } from './TablaLista'
import tablaSource from './TablaLista.tsx?raw'

const COLUMNAS = [
  'Prioridad',
  'Nombre',
  'Cédula',
  'Plan',
  'Vence el',
  'Días para vencer',
  'Nivel de riesgo',
  'Motivos principales',
  'Gestión',
  'Campaña',
  'Acción',
]

function item(prioridad: number, extra: Partial<Prediccion> = {}): Prediccion {
  return {
    prediccionId: 100 + prioridad,
    prioridad,
    socioNombre: `Socio Ficticio ${prioridad}`,
    celular: `09900000${prioridad}0`,
    cedula: `00000000${prioridad}0`,
    plan: 'MENSUAL',
    fechaVencimiento: '2026-10-05',
    diasParaVencer: 6,
    montoCobrado: '30.00',
    score: `0.${9 - prioridad}1234567`,
    nivelRiesgo: 'ALTO',
    factoresPrincipales: ['Plan: TRIMESTRAL (+0,09)', 'Ciclos previos: 1.234 (+0,12)'],
    dentroTopK: prioridad <= 2,
    gestionId: null,
    gestionEstado: null,
    campaniaAsignada: null,
    ...extra,
  }
}

function lista(items: Prediccion[], topK = 2, nombre = 'Campaña octubre'): ListaPriorizada {
  return {
    id: 7,
    nombre,
    modeloVersion: 'v1',
    fechaGeneracion: '2026-09-29',
    creadaEn: new Date('2026-09-29T15:00:00Z'),
    horizonteDias: 30,
    topK,
    umbralAlto: '0.70000000',
    umbralMedio: '0.40000000',
    advertenciaDatosAntiguos: false,
    items,
  }
}

/** 5 items, desordenados a proposito; los 2 primeros por prioridad estan dentro del top. */
const CINCO = [item(4), item(1), item(5), item(2), item(3)]

function tabla(nombre: string) {
  return within(screen.getByRole('table', { name: nombre }))
}

function nombres(nombreTabla: string): string[] {
  return tabla(nombreTabla)
    .getAllByRole('row')
    .slice(1)
    .map((fila) => within(fila).getAllByRole('cell')[1]?.textContent ?? '')
}

describe('TablaLista', () => {
  afterEach(() => {
    cleanup()
  })

  it('encabezado con el nombre de la lista y resumen sin terminos tecnicos', () => {
    render(<TablaLista lista={lista(CINCO)} />)

    expect(
      screen.getByRole('heading', { level: 2, name: 'Campaña octubre' }),
    ).toBeInTheDocument()
    expect(document.body.textContent).not.toContain('Lista del 29 de septiembre de 2026')
    const rango = screen.getByText('Rango de fechas: 29 sep – 29 oct 2026')
    const resumen = rango.parentElement as HTMLElement
    expect(Array.from(resumen.children).map((p) => p.textContent)).toEqual([
      'Rango de fechas: 29 sep – 29 oct 2026',
      'Socios priorizados para campañas: 2',
    ])
    expect(document.body.textContent).not.toMatch(/v1|versi[oó]n del modelo|top k|horizonte/i)
    expect(document.body.textContent).not.toContain('Socios por vencer en los próximos')
    expect(document.body.textContent).not.toContain('Socios prioritarios a contactar: ')
  })

  it('nombre con HTML → se muestra como texto literal', () => {
    render(<TablaLista lista={lista(CINCO, 2, '<b>x</b>')} />)

    const titulo = screen.getByRole('heading', { level: 2, name: '<b>x</b>' })
    expect(titulo.textContent).toBe('<b>x</b>')
    expect(titulo.querySelector('b')).toBeNull()
  })

  it('30 items con 25 prioritarios → "Socios priorizados para campañas: 25"', () => {
    const treinta = Array.from({ length: 30 }, (_, i) => item(i + 1, { dentroTopK: i < 25 }))
    render(<TablaLista lista={lista(treinta, 25)} />)

    expect(screen.getByText('Rango de fechas: 29 sep – 29 oct 2026')).toBeInTheDocument()
    expect(screen.getByText('Socios priorizados para campañas: 25')).toBeInTheDocument()
  })

  it('no muestra la columna Celular ni ningun numero de celular', () => {
    render(<TablaLista lista={lista(CINCO)} />)

    expect(screen.queryByRole('columnheader', { name: 'Celular' })).not.toBeInTheDocument()
    const texto = document.body.textContent ?? ''
    expect(texto).not.toMatch(/celular/i)
    for (const p of CINCO) expect(texto).not.toContain(p.celular as string)
  })

  it('dos tablas: prioritarios (dentroTopK) y otros, ambas en orden de prioridad', () => {
    render(<TablaLista lista={lista(CINCO)} />)

    expect(screen.getAllByRole('table')).toHaveLength(2)
    expect(nombres('Socios prioritarios a contactar')).toEqual([
      'Socio Ficticio 1',
      'Socio Ficticio 2',
    ])
    expect(nombres('Otros socios por vencer')).toEqual([
      'Socio Ficticio 3',
      'Socio Ficticio 4',
      'Socio Ficticio 5',
    ])
  })

  it('con 0 socios fuera de los prioritarios no se muestra la segunda tabla', () => {
    render(<TablaLista lista={lista([item(1), item(2)])} />)

    expect(screen.getAllByRole('table')).toHaveLength(1)
    expect(screen.queryByRole('table', { name: 'Otros socios por vencer' })).not.toBeInTheDocument()
  })

  it('columnas exactas en ambas tablas: con cedula, sin correo, indicador ni Top', () => {
    render(<TablaLista lista={lista(CINCO)} />)

    for (const nombre of ['Socios prioritarios a contactar', 'Otros socios por vencer']) {
      const cabeceras = tabla(nombre)
        .getAllByRole('columnheader')
        .map((th) => th.textContent)
      expect(cabeceras).toEqual(COLUMNAS)
    }
    const texto = document.body.textContent ?? ''
    expect(texto).not.toMatch(/correo|indicador de prioridad|\btop\b/i)
  })

  it('el score no se renderiza en ningun lugar', () => {
    render(<TablaLista lista={lista(CINCO)} />)

    const texto = document.body.textContent ?? ''
    for (const p of CINCO) expect(texto).not.toContain(p.score)
    expect(texto).not.toMatch(/score/i)
  })

  it('motivos sin el aporte entre parentesis; [] → texto por defecto', () => {
    render(
      <TablaLista
        lista={lista([
          item(1),
          item(2, { factoresPrincipales: ['Pocas renovaciones previas'] }),
          item(3, { factoresPrincipales: [] }),
        ])}
      />,
    )

    const prioritarios = tabla('Socios prioritarios a contactar')
    expect(prioritarios.getAllByText('Plan: TRIMESTRAL')).toHaveLength(1)
    expect(prioritarios.getByText('Ciclos previos: 1.234')).toBeInTheDocument()
    expect(prioritarios.getByText('Pocas renovaciones previas')).toBeInTheDocument()
    expect(tabla('Otros socios por vencer').getByText('Sin factores de riesgo destacados')).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/\(\+0,/)
  })

  it.each([
    ['Plan: TRIMESTRAL (+0,09)', 'Plan: TRIMESTRAL'],
    ['Ciclos previos: 1.234 (+0,12)', 'Ciclos previos: 1.234'],
    ['Pocas renovaciones previas', 'Pocas renovaciones previas'],
    ['Plan (MENSUAL) y poca asistencia', 'Plan (MENSUAL) y poca asistencia'],
  ])('motivo %j se muestra como %j', (entrada, esperado) => {
    render(<TablaLista lista={lista([item(1, { factoresPrincipales: [entrada] })])} />)

    const celda = tabla('Socios prioritarios a contactar').getByRole('listitem')
    expect(celda.textContent).toBe(esperado)
  })

  it('cedula con cero inicial se muestra tal cual; cedula null → "—"', () => {
    render(
      <TablaLista
        lista={lista([item(1, { cedula: '0012345678' }), item(2, { cedula: null })])}
      />,
    )

    const filas = tabla('Socios prioritarios a contactar').getAllByRole('row').slice(1)
    expect(within(filas[0] as HTMLElement).getAllByRole('cell')[2]).toHaveTextContent(
      /^0012345678$/,
    )
    expect(within(filas[1] as HTMLElement).getAllByRole('cell')[2]).toHaveTextContent(/^—$/)
  })

  it('lista vacia → tabla de prioritarios con mensaje y resumen en 0', () => {
    render(<TablaLista lista={lista([])} />)

    expect(screen.getByText('Rango de fechas: 29 sep – 29 oct 2026')).toBeInTheDocument()
    expect(screen.getByText('Socios priorizados para campañas: 0')).toBeInTheDocument()
    expect(screen.getByText('No hay socios cuya membresía venza en esos días.')).toBeInTheDocument()
  })

  describe('gestion (D5-FE-03)', () => {
    const TRES = [
      item(1),
      item(2, {
        gestionId: 9,
        gestionEstado: 'PENDIENTE',
        campaniaAsignada: 'Ejemplo: Renovación anticipada',
      }),
      item(3, { gestionId: 10, gestionEstado: 'CERRADA', campaniaAsignada: null }),
    ]

    function celdas(nombreTabla: string, fila: number) {
      const filas = tabla(nombreTabla).getAllByRole('row').slice(1)
      return within(filas[fila] as HTMLElement).getAllByRole('cell')
    }

    it('columnas "Gestión" y "Campaña": sin gestion, pendiente con campaña y cerrada sin campaña', () => {
      render(<TablaLista lista={lista(TRES)} />)

      const textos = (nombreTabla: string, fila: number) =>
        celdas(nombreTabla, fila)
          .slice(8, 10)
          .map((c) => c.textContent)
      expect(textos(TITULO_PRIORITARIOS, 0)).toEqual(['Sin gestión', '—'])
      expect(textos(TITULO_PRIORITARIOS, 1)).toEqual([
        'Pendiente',
        'Ejemplo: Renovación anticipada',
      ])
      expect(textos(TITULO_OTROS, 0)).toEqual(['Cerrada', 'Sin campaña'])
    })

    it('botones con la prioridad (sin el nombre del socio) en ambas tablas', () => {
      render(<TablaLista lista={lista(TRES)} />)

      expect(
        tabla(TITULO_PRIORITARIOS).getByRole('button', { name: 'Gestionar prioridad 1' }),
      ).toHaveTextContent(/^Gestionar$/)
      expect(
        tabla(TITULO_PRIORITARIOS).getByRole('button', { name: 'Registrar resultado prioridad 2' }),
      ).toBeInTheDocument()
      expect(
        tabla(TITULO_OTROS).getByRole('button', { name: 'Ver gestión prioridad 3' }),
      ).toBeInTheDocument()
      for (const boton of screen.getAllByRole('button')) {
        expect(boton.getAttribute('aria-label')).not.toMatch(/Socio Ficticio/)
      }
    })

    it('fila cerrada sin campaña: la unica accion es "Ver gestión"', () => {
      render(<TablaLista lista={lista(TRES)} />)

      const fila = tabla(TITULO_OTROS).getAllByRole('row')[1] as HTMLElement
      expect(
        within(fila)
          .getAllByRole('button')
          .map((b) => [b.getAttribute('aria-label'), b.textContent]),
      ).toEqual([['Ver gestión prioridad 3', 'Ver gestión']])
      expect(within(fila).queryByRole('button', { name: /Registrar resultado/ })).not.toBeInTheDocument()
      expect(within(fila).queryByRole('button', { name: /^Gestionar/ })).not.toBeInTheDocument()
    })

    it('el boton emite onGestionar con la prediccion de su fila', async () => {
      const user = userEvent.setup()
      const onGestionar = vi.fn()
      render(<TablaLista lista={lista(TRES)} onGestionar={onGestionar} />)

      await user.click(screen.getByRole('button', { name: 'Ver gestión prioridad 3' }))

      expect(onGestionar).toHaveBeenCalledTimes(1)
      expect(onGestionar).toHaveBeenCalledWith(TRES[2])
    })

    it('nombre de campaña con HTML → texto literal', () => {
      render(
        <TablaLista
          lista={lista([
            item(1, { gestionId: 1, gestionEstado: 'PENDIENTE', campaniaAsignada: '<b>x</b>' }),
          ])}
        />,
      )

      const celda = celdas(TITULO_PRIORITARIOS, 0)[9] as HTMLElement
      expect(celda.textContent).toBe('<b>x</b>')
      expect(celda.querySelector('b')).toBeNull()
    })
  })

  it('arquitectura: presentacional y sin convertir decimales a numero', () => {
    expect(tablaSource).not.toMatch(/from\s+['"][^'"]*\/(api|hooks)\//)
    expect(tablaSource).not.toMatch(/\buse[A-Z]\w*\s*\(/)
    expect(tablaSource).not.toMatch(/parseFloat|Number\(|\.score\b/)
  })
})
