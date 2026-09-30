import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CampaniaSugerida, Gestion, Prediccion } from '../types'
import { type FormularioGestionProps, FormularioGestion } from './FormularioGestion'
import formularioSource from './FormularioGestion.tsx?raw'
import resultadoSource from './ResultadoGestion.tsx?raw'

const HOY = '2026-09-29'

const PREDICCION: Prediccion = {
  prediccionId: 1503,
  prioridad: 3,
  socioNombre: 'Socio Ficticio',
  celular: null,
  cedula: '0000000002',
  plan: 'MENSUAL',
  fechaVencimiento: '2026-10-05',
  diasParaVencer: 6,
  montoCobrado: '30.00',
  score: '0.89000000',
  nivelRiesgo: 'ALTO',
  factoresPrincipales: [],
  dentroTopK: true,
  gestionId: null,
  gestionEstado: null,
  campaniaAsignada: null,
}

const SUGERIDAS: CampaniaSugerida[] = [
  {
    id: 1,
    nombre: 'Ejemplo: Llamada personal antes del vencimiento',
    descripcion: 'Llamar al socio antes de que venza su plan.',
    prioridad: 1,
  },
  { id: 2, nombre: 'Ejemplo: Renovación anticipada', descripcion: null, prioridad: 2 },
]

function gestion(extra: Partial<Gestion> = {}): Gestion {
  return {
    id: 9,
    prediccionId: 1503,
    socioNombre: 'Socio Ficticio',
    plan: 'MENSUAL',
    fechaVencimiento: '2026-10-05',
    modeloVersion: 'v1',
    score: '0.89000000',
    nivelRiesgo: 'ALTO',
    campaniaId: 2,
    campaniaNombre: 'Ejemplo: Renovación anticipada',
    estado: 'PENDIENTE',
    fechaAsignacion: new Date(2026, 8, 28, 10, 0, 0),
    fechaSeguimiento: '2026-10-30',
    responsable: 'Andrea',
    contactado: null,
    campaniaOfrecida: null,
    campaniaAceptada: null,
    renovoDeclarado: null,
    fechaContacto: null,
    observaciones: null,
    fechaCierre: null,
    ...extra,
  }
}

function renderFormulario(props: Partial<FormularioGestionProps> = {}) {
  const onCrear = vi.fn()
  const onRegistrar = vi.fn()
  const onCerrar = vi.fn()
  render(
    <FormularioGestion
      prediccion={PREDICCION}
      hoy={HOY}
      estado="listo"
      sugeridas={SUGERIDAS}
      gestion={null}
      error={null}
      onCrear={onCrear}
      onRegistrar={onRegistrar}
      onCerrar={onCerrar}
      {...props}
    />,
  )
  return { onCrear, onRegistrar, onCerrar, dialogo: within(screen.getByRole('dialog')) }
}

function grupo(nombre: string) {
  return within(screen.getByRole('group', { name: nombre }))
}

describe('FormularioGestion', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 8, 29, 12, 0, 0))
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  describe('parte 1: crear la gestion', () => {
    it('titulo con la prioridad; plan, vencimiento y nivel con RiskBadge', () => {
      const { dialogo } = renderFormulario()

      expect(screen.getByRole('dialog', { name: 'Gestión de la prioridad 3' })).toBeInTheDocument()
      expect(dialogo.getByText('Plan: MENSUAL')).toBeInTheDocument()
      expect(dialogo.getByText('Vence el 5 oct 2026')).toBeInTheDocument()
      expect(dialogo.getByText('Alto')).toBeInTheDocument()
      // Ni el score ni la cedula se muestran.
      expect(document.body.textContent).not.toMatch(/0\.89|0000000002/)
    })

    it('radios de las sugeridas en orden + "No asignar campaña", ninguna marcada', () => {
      renderFormulario()

      const radios = grupo('Campaña').getAllByRole('radio')
      expect(radios.map((r) => r.closest('label')?.textContent)).toEqual([
        'Ejemplo: Llamada personal antes del vencimiento',
        'Ejemplo: Renovación anticipada',
        'No asignar campaña',
      ])
      expect(radios.every((r) => !(r as HTMLInputElement).checked)).toBe(true)
      expect(
        screen.getByRole('radio', { name: 'Ejemplo: Llamada personal antes del vencimiento' }),
      ).toHaveAccessibleDescription('Llamar al socio antes de que venza su plan.')
    })

    it('sin sugerencias → solo "No asignar campaña", marcada', () => {
      renderFormulario({ sugeridas: [] })

      const radios = grupo('Campaña').getAllByRole('radio')
      expect(radios).toHaveLength(1)
      expect(screen.getByRole('radio', { name: 'No asignar campaña' })).toBeChecked()
    })

    it('fecha de seguimiento = sugerida con min y max del rango', () => {
      renderFormulario()

      const fecha = screen.getByLabelText('Fecha de seguimiento')
      expect(fecha).toHaveAttribute('type', 'date')
      expect(fecha).toHaveValue('2026-10-30')
      expect(fecha).toHaveAttribute('min', '2026-09-29')
      expect(fecha).toHaveAttribute('max', '2026-11-04')
      expect(screen.getByLabelText('Responsable (opcional)')).toHaveAttribute('maxLength', '120')
    })

    it('fecha 2026-11-05 → mensaje con el rango, enlazado al campo, sin enviar', async () => {
      const user = userEvent.setup()
      const { onCrear } = renderFormulario()
      // Con campaña: sin campaña el campo de fecha no existe (R-010).
      await user.click(screen.getByRole('radio', { name: 'Ejemplo: Renovación anticipada' }))
      const fecha = screen.getByLabelText('Fecha de seguimiento')
      fireEvent.change(fecha, { target: { value: '2026-11-05' } })

      await user.click(screen.getByRole('button', { name: 'Crear gestión' }))

      const mensaje = 'La fecha de seguimiento debe estar entre el 29/09/2026 y el 04/11/2026.'
      expect(screen.getByText(mensaje)).toBeInTheDocument()
      expect(fecha).toHaveAccessibleDescription(expect.stringContaining(mensaje))
      expect(fecha).toHaveAttribute('aria-invalid', 'true')
      expect(onCrear).not.toHaveBeenCalled()
    })

    it('con sugerencias y sin elegir → mensaje en el grupo, sin enviar', async () => {
      const user = userEvent.setup()
      const { onCrear } = renderFormulario()

      await user.click(screen.getByRole('button', { name: 'Crear gestión' }))

      expect(screen.getByRole('group', { name: 'Campaña' })).toHaveAccessibleDescription(
        'Elija una campaña o «No asignar campaña».',
      )
      expect(onCrear).not.toHaveBeenCalled()
    })

    it('valida → emite campaña, fecha y responsable recortado', async () => {
      const user = userEvent.setup()
      const { onCrear } = renderFormulario()

      await user.click(screen.getByRole('radio', { name: 'Ejemplo: Renovación anticipada' }))
      await user.type(screen.getByLabelText('Responsable (opcional)'), '  Andrea  ')
      await user.click(screen.getByRole('button', { name: 'Crear gestión' }))

      expect(onCrear).toHaveBeenCalledWith({
        campaniaId: 2,
        fechaSeguimiento: '2026-10-30',
        responsable: 'Andrea',
      })
    })

    it('con campaña y responsable vacio → responsable null', async () => {
      const user = userEvent.setup()
      const { onCrear } = renderFormulario()

      await user.click(screen.getByRole('radio', { name: 'Ejemplo: Renovación anticipada' }))
      await user.type(screen.getByLabelText('Responsable (opcional)'), '   ')
      await user.click(screen.getByRole('button', { name: 'Crear gestión' }))

      expect(onCrear).toHaveBeenCalledWith({
        campaniaId: 2,
        fechaSeguimiento: '2026-10-30',
        responsable: null,
      })
    })

    it('"No asignar campaña" → emite campaniaId, fechaSeguimiento y responsable null', async () => {
      const user = userEvent.setup()
      const { onCrear } = renderFormulario()

      // Lo escrito antes de elegir "No asignar campaña" no viaja.
      await user.type(screen.getByLabelText('Responsable (opcional)'), 'Andrea')
      await user.click(screen.getByRole('radio', { name: 'No asignar campaña' }))
      await user.click(screen.getByRole('button', { name: 'Crear gestión' }))

      expect(onCrear).toHaveBeenCalledTimes(1)
      expect(onCrear).toHaveBeenCalledWith({
        campaniaId: null,
        fechaSeguimiento: null,
        responsable: null,
      })
    })

    it('"No asignar campaña" oculta fecha y responsable y muestra el aviso; con campaña vuelven', async () => {
      const user = userEvent.setup()
      renderFormulario()
      const aviso = 'Sin campaña, la gestión queda cerrada y no tendrá seguimiento.'
      expect(screen.queryByText(aviso)).not.toBeInTheDocument()

      await user.click(screen.getByRole('radio', { name: 'No asignar campaña' }))

      expect(screen.queryByLabelText('Fecha de seguimiento')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Responsable (opcional)')).not.toBeInTheDocument()
      expect(screen.getByText(aviso)).toBeInTheDocument()

      await user.click(screen.getByRole('radio', { name: 'Ejemplo: Renovación anticipada' }))

      expect(screen.getByLabelText('Fecha de seguimiento')).toHaveValue('2026-10-30')
      expect(screen.getByLabelText('Responsable (opcional)')).toBeInTheDocument()
      expect(screen.queryByText(aviso)).not.toBeInTheDocument()
    })

    it('sin sugerencias → "No asignar campaña" marcada: sin fecha ni responsable y con el aviso', () => {
      renderFormulario({ sugeridas: [] })

      expect(screen.queryByLabelText('Fecha de seguimiento')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Responsable (opcional)')).not.toBeInTheDocument()
      expect(
        screen.getByText('Sin campaña, la gestión queda cerrada y no tendrá seguimiento.'),
      ).toBeInTheDocument()
    })

    it('plazo terminado → mensaje y "Crear gestión" deshabilitado', () => {
      renderFormulario({ prediccion: { ...PREDICCION, fechaVencimiento: '2026-08-29' } })

      expect(screen.getByText('El plazo de seguimiento de este ciclo ya terminó.')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Crear gestión' })).toBeDisabled()
    })

    it('plazo terminado → "Crear gestión" solo se habilita con "No asignar campaña" y crea sin fecha', async () => {
      const user = userEvent.setup()
      const { onCrear } = renderFormulario({
        prediccion: { ...PREDICCION, fechaVencimiento: '2026-08-29' },
      })
      const crear = screen.getByRole('button', { name: 'Crear gestión' })

      await user.click(screen.getByRole('radio', { name: 'Ejemplo: Renovación anticipada' }))
      expect(crear).toBeDisabled()

      await user.click(screen.getByRole('radio', { name: 'No asignar campaña' }))
      expect(crear).toBeEnabled()
      expect(
        screen.queryByText('El plazo de seguimiento de este ciclo ya terminó.'),
      ).not.toBeInTheDocument()
      await user.click(crear)

      expect(onCrear).toHaveBeenCalledWith({
        campaniaId: null,
        fechaSeguimiento: null,
        responsable: null,
      })
    })

    it('enviando → "Crear gestión" deshabilitado; error del servidor → ErrorAlert', () => {
      renderFormulario({ estado: 'enviando', error: 'El ciclo de membresia ya tiene una gestion.' })

      expect(screen.getByRole('button', { name: 'Crear gestión' })).toBeDisabled()
      expect(screen.getByRole('alert')).toHaveTextContent('El ciclo de membresia ya tiene una gestion.')
    })

    it('cargando → indicador y sin formulario; error de carga → ErrorAlert con Reintentar', async () => {
      const user = userEvent.setup()
      renderFormulario({ estado: 'cargando' })
      expect(screen.getByRole('status')).toHaveTextContent('Cargando la gestión')
      expect(screen.queryByRole('button', { name: 'Crear gestión' })).not.toBeInTheDocument()
      cleanup()

      const onReintentar = vi.fn()
      renderFormulario({ estado: 'error', error: 'Fallo simulado.', onReintentar })
      await user.click(screen.getByRole('button', { name: 'Reintentar' }))
      expect(onReintentar).toHaveBeenCalledTimes(1)
    })
  })

  describe('parte 2: resultado de una gestion pendiente', () => {
    it('elegir "No" en contactado deja oferta y aceptacion en "No aplica" y deshabilita las demas', async () => {
      const user = userEvent.setup()
      renderFormulario({ gestion: gestion() })

      await user.click(grupo('¿Se contactó al socio?').getByRole('radio', { name: 'No' }))

      for (const nombre of ['¿Se ofreció la campaña?', '¿Aceptó la campaña?']) {
        expect(grupo(nombre).getByRole('radio', { name: 'No aplica' })).toBeChecked()
        for (const radio of grupo(nombre).getAllByRole('radio')) {
          if ((radio as HTMLInputElement).value !== 'NO_APLICA') expect(radio).toBeDisabled()
        }
      }
      expect(screen.getByLabelText('Fecha del contacto')).toBeDisabled()
    })

    it('gestion sin campaña → oferta y aceptacion en "No aplica" y el resto deshabilitado', () => {
      renderFormulario({ gestion: gestion({ campaniaId: null, campaniaNombre: null }) })

      expect(screen.getByText('Sin campaña')).toBeInTheDocument()
      for (const nombre of ['¿Se ofreció la campaña?', '¿Aceptó la campaña?']) {
        expect(grupo(nombre).getByRole('radio', { name: 'No aplica' })).toBeChecked()
        expect(grupo(nombre).getByRole('radio', { name: 'Sí' })).toBeDisabled()
        expect(grupo(nombre).getByRole('radio', { name: 'No' })).toBeDisabled()
      }
    })

    it('ofrecida "Sí" → aceptacion Sí/No/Pendiente; ofrecida "No" → solo "No aplica"', async () => {
      const user = userEvent.setup()
      renderFormulario({ gestion: gestion() })
      await user.click(grupo('¿Se contactó al socio?').getByRole('radio', { name: 'Sí' }))

      await user.click(grupo('¿Se ofreció la campaña?').getByRole('radio', { name: 'Sí' }))
      const aceptada = grupo('¿Aceptó la campaña?')
      expect(aceptada.getByRole('radio', { name: 'Pendiente' })).toBeEnabled()
      expect(aceptada.getByRole('radio', { name: 'No aplica' })).toBeDisabled()

      await user.click(grupo('¿Se ofreció la campaña?').getByRole('radio', { name: 'No' }))
      expect(aceptada.getByRole('radio', { name: 'No aplica' })).toBeChecked()
      expect(aceptada.getByRole('radio', { name: 'Sí' })).toBeDisabled()
    })

    it('"Fecha de seguimiento" solo visible con Renovó = Pendiente', async () => {
      const user = userEvent.setup()
      renderFormulario({ gestion: gestion() })
      const renovo = grupo('¿Renovó?')

      expect(screen.queryByLabelText('Fecha de seguimiento')).not.toBeInTheDocument()
      await user.click(renovo.getByRole('radio', { name: 'Pendiente' }))
      expect(screen.getByLabelText('Fecha de seguimiento')).toHaveValue('2026-10-30')
      await user.click(renovo.getByRole('radio', { name: 'No' }))
      expect(screen.queryByLabelText('Fecha de seguimiento')).not.toBeInTheDocument()
    })

    it('Guardar con Renovó = No → emite el resultado', async () => {
      const user = userEvent.setup()
      const { onRegistrar } = renderFormulario({ gestion: gestion() })

      await user.click(grupo('¿Se contactó al socio?').getByRole('radio', { name: 'No' }))
      await user.click(grupo('¿Renovó?').getByRole('radio', { name: 'No' }))
      await user.type(screen.getByLabelText('Observaciones'), 'No contesta')
      await user.click(screen.getByRole('button', { name: 'Guardar resultado' }))

      expect(onRegistrar).toHaveBeenCalledWith({
        contactado: false,
        campaniaOfrecida: 'NO_APLICA',
        campaniaAceptada: 'NO_APLICA',
        renovoDeclarado: 'NO',
        fechaContacto: null,
        observaciones: 'No contesta',
        responsable: 'Andrea',
        fechaSeguimiento: null,
      })
    })

    it('contactado Sí sin fecha de contacto → "Indique la fecha del contacto." sin enviar', async () => {
      const user = userEvent.setup()
      const { onRegistrar } = renderFormulario({ gestion: gestion() })

      await user.click(grupo('¿Se contactó al socio?').getByRole('radio', { name: 'Sí' }))
      await user.click(grupo('¿Se ofreció la campaña?').getByRole('radio', { name: 'Sí' }))
      await user.click(grupo('¿Aceptó la campaña?').getByRole('radio', { name: 'Pendiente' }))
      await user.click(grupo('¿Renovó?').getByRole('radio', { name: 'Pendiente' }))
      await user.click(screen.getByRole('button', { name: 'Guardar resultado' }))

      const fechaContacto = screen.getByLabelText('Fecha del contacto')
      expect(fechaContacto).toHaveAccessibleDescription('Indique la fecha del contacto.')
      expect(onRegistrar).not.toHaveBeenCalled()

      fireEvent.change(fechaContacto, { target: { value: HOY } })
      await user.click(screen.getByRole('button', { name: 'Guardar resultado' }))
      expect(onRegistrar).toHaveBeenCalledWith(
        expect.objectContaining({ contactado: true, fechaContacto: HOY, campaniaAceptada: 'PENDIENTE' }),
      )
    })

    it('enviando → "Guardar resultado" deshabilitado (sin doble envio)', async () => {
      const user = userEvent.setup()
      const { onRegistrar } = renderFormulario({ gestion: gestion(), estado: 'enviando' })

      const guardar = screen.getByRole('button', { name: 'Guardar resultado' })
      expect(guardar).toBeDisabled()
      await user.click(guardar)
      expect(onRegistrar).not.toHaveBeenCalled()
    })

    it.each([
      ['422', 'Si no se ofreció la campaña, la aceptación debe ser «No aplica».'],
      ['409', 'La gestion esta cerrada y no se puede modificar.'],
    ])('%s del servidor al registrar → ErrorAlert con su mensaje y el formulario sigue', (_s, mensaje) => {
      renderFormulario({ gestion: gestion(), error: mensaje })

      expect(screen.getByRole('alert')).toHaveTextContent(mensaje)
      expect(screen.getByRole('button', { name: 'Guardar resultado' })).toBeEnabled()
    })

    it('Observaciones maxLength 500 y Responsable 120', () => {
      renderFormulario({ gestion: gestion() })

      expect(screen.getByLabelText('Observaciones')).toHaveAttribute('maxLength', '500')
      expect(screen.getByLabelText('Responsable')).toHaveAttribute('maxLength', '120')
    })
  })

  it('gestion cerrada → todo de solo lectura, sin "Guardar" y con el aviso', () => {
    renderFormulario({
      gestion: gestion({
        estado: 'CERRADA',
        contactado: true,
        campaniaOfrecida: 'SI',
        campaniaAceptada: 'NO',
        renovoDeclarado: 'NO',
        fechaContacto: '2026-09-28',
        observaciones: 'Se muda de ciudad.',
        fechaCierre: new Date(2026, 8, 28, 15, 0, 0),
      }),
    })

    expect(screen.getByText('Gestión cerrada: no se puede modificar.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Guardar resultado' })).not.toBeInTheDocument()
    const formulario = within(screen.getByRole('form', { name: 'Resultado del seguimiento' }))
    const campos = [
      ...formulario.getAllByRole('radio'),
      ...formulario.getAllByRole('textbox'),
      screen.getByLabelText('Fecha del contacto'),
    ]
    for (const campo of campos) expect(campo).toBeDisabled()
    expect(grupo('¿Renovó?').getByRole('radio', { name: 'No' })).toBeChecked()
    expect(screen.getByLabelText('Observaciones')).toHaveValue('Se muda de ciudad.')
  })

  it('gestion cerrada sin campaña → solo "No se le asignó campaña": sin preguntas, campos ni guardar', () => {
    const { dialogo } = renderFormulario({
      gestion: gestion({
        estado: 'CERRADA',
        campaniaId: null,
        campaniaNombre: null,
        responsable: null,
        fechaSeguimiento: '2026-09-28',
        fechaCierre: new Date(2026, 8, 28, 10, 0, 0),
      }),
    })

    expect(dialogo.getByText('No se le asignó campaña')).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Resultado del seguimiento' })).not.toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Nueva gestión' })).not.toBeInTheDocument()
    expect(dialogo.queryAllByRole('radio')).toHaveLength(0)
    expect(dialogo.queryAllByRole('textbox')).toHaveLength(0)
    expect(dialogo.queryAllByRole('group')).toHaveLength(0)
    expect(document.querySelectorAll('input, textarea, select')).toHaveLength(0)
    expect(dialogo.queryByRole('button', { name: 'Guardar resultado' })).not.toBeInTheDocument()
    expect(dialogo.queryByRole('button', { name: 'Crear gestión' })).not.toBeInTheDocument()
    expect(dialogo.getAllByRole('button').map((b) => b.textContent)).toEqual(['Cerrar'])
    expect(dialogo.queryByText('Gestión cerrada: no se puede modificar.')).not.toBeInTheDocument()
  })

  describe('accesibilidad y foco', () => {
    it('cada grupo de radios es un fieldset con legend', () => {
      renderFormulario({ gestion: gestion() })

      for (const nombre of ['¿Se contactó al socio?', '¿Se ofreció la campaña?', '¿Aceptó la campaña?', '¿Renovó?']) {
        const fieldset = screen.getByRole('group', { name: nombre })
        expect(fieldset.tagName).toBe('FIELDSET')
        expect(fieldset.querySelector('legend')).toHaveTextContent(nombre)
      }
    })

    it('al abrir el foco va al primer campo; al cerrar vuelve al boton que la abrio', async () => {
      const user = userEvent.setup()
      function Contenedor() {
        const [abierta, setAbierta] = useState(false)
        return (
          <>
            <button type="button" onClick={() => setAbierta(true)}>
              Gestionar prioridad 3
            </button>
            {abierta && (
              <FormularioGestion
                prediccion={PREDICCION}
                hoy={HOY}
                estado="listo"
                sugeridas={SUGERIDAS}
                gestion={null}
                error={null}
                onCrear={() => {}}
                onRegistrar={() => {}}
                onCerrar={() => setAbierta(false)}
              />
            )}
          </>
        )
      }
      render(<Contenedor />)
      const boton = screen.getByRole('button', { name: 'Gestionar prioridad 3' })

      await user.click(boton)
      expect(
        screen.getByRole('radio', { name: 'Ejemplo: Llamada personal antes del vencimiento' }),
      ).toHaveFocus()

      await user.click(screen.getByRole('button', { name: 'Cerrar' }))
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
      expect(boton).toHaveFocus()
    })

    it('guardar el resultado sin responder → errores en los grupos enlazados con aria-describedby', async () => {
      const user = userEvent.setup()
      const { onRegistrar } = renderFormulario({ gestion: gestion() })

      await user.click(screen.getByRole('button', { name: 'Guardar resultado' }))

      expect(screen.getByRole('group', { name: '¿Se contactó al socio?' })).toHaveAccessibleDescription(
        'Indique si se contactó al socio.',
      )
      expect(screen.getByRole('group', { name: '¿Renovó?' })).toHaveAccessibleDescription(
        'Indique si el socio renovó.',
      )
      expect(onRegistrar).not.toHaveBeenCalled()
    })

    it.each([
      ['parte 1', null],
      ['parte 2', gestion()],
      ['cerrada', gestion({ estado: 'CERRADA', renovoDeclarado: 'SI', fechaCierre: new Date(2026, 8, 28) })],
    ])('%s: el nombre del socio no aparece en ningun aria-label ni en el nombre del dialogo', (_p, g) => {
      renderFormulario({ gestion: g })

      expect(screen.getByRole('dialog')).toHaveAccessibleName('Gestión de la prioridad 3')
      for (const el of document.querySelectorAll('[aria-label]')) {
        expect(el.getAttribute('aria-label')).not.toMatch(/Socio Ficticio/)
      }
    })

    it('Escape → onCerrar', async () => {
      const user = userEvent.setup()
      const { onCerrar } = renderFormulario()

      await user.keyboard('{Escape}')

      expect(onCerrar).toHaveBeenCalledTimes(1)
    })
  })

  it('arquitectura: presentacional (sin api/, core/http ni hooks de datos) y sin CSS nuevo', () => {
    for (const fuente of [formularioSource, resultadoSource]) {
      expect(fuente).not.toMatch(/from\s+['"][^'"]*\/api\//)
      expect(fuente).not.toMatch(/core\/http|\bfetch\s*\(/)
      // Solo las reglas puras de `hooks/reglasGestion`, nunca un hook de datos.
      expect(fuente).not.toMatch(/from\s+['"][^'"]*\/hooks\/use[A-Z]/)
      expect(fuente).not.toMatch(/style=\{|\.css['"]/)
      expect(fuente).not.toMatch(/\.score\b|parseFloat/)
    }
  })
})
