import { describe, expect, it } from 'vitest'
import {
  type BorradorResultado,
  type ContextoResultado,
  ajustarRespuestas,
  fechaLocalIso,
  fechaSugerida,
  MENSAJE_FECHA_CONTACTO,
  MENSAJE_PLAZO_TERMINADO,
  opcionesPermitidas,
  rangoSeguimiento,
  validarFechaSeguimiento,
  validarResultado,
} from './reglasGestion'
import source from './reglasGestion.ts?raw'

const HOY = '2026-09-29'

describe('reglasGestion: rango y fecha sugerida (mismos casos que el dominio del backend)', () => {
  it('vencimiento 2026-10-05 → rango 2026-09-29..2026-11-04 y sugerida 2026-10-30', () => {
    expect(rangoSeguimiento(HOY, '2026-10-05')).toEqual({ desde: HOY, hasta: '2026-11-04' })
    expect(fechaSugerida(HOY, '2026-10-05')).toBe('2026-10-30')
  })

  it('vencimiento 2026-09-01 → rango 2026-09-29..2026-10-01 y sugerida hoy', () => {
    expect(rangoSeguimiento(HOY, '2026-09-01')).toEqual({ desde: HOY, hasta: '2026-10-01' })
    expect(fechaSugerida(HOY, '2026-09-01')).toBe(HOY)
  })

  it('vencimiento 2026-08-29 (vencimiento + 30 < hoy) → sin rango ni sugerida; plazo terminado', () => {
    expect(rangoSeguimiento(HOY, '2026-08-29')).toBeNull()
    expect(fechaSugerida(HOY, '2026-08-29')).toBeNull()
    expect(validarFechaSeguimiento(HOY, HOY, '2026-08-29')).toBe(
      'El plazo de seguimiento de este ciclo ya terminó.',
    )
    expect(MENSAJE_PLAZO_TERMINADO).toBe('El plazo de seguimiento de este ciclo ya terminó.')
  })

  it('vencimiento + 30 = hoy → rango de un solo dia', () => {
    expect(rangoSeguimiento(HOY, '2026-08-30')).toEqual({ desde: HOY, hasta: HOY })
  })

  it('cruza de año sin desplazarse por zona horaria', () => {
    expect(rangoSeguimiento('2026-12-20', '2026-12-31')).toEqual({
      desde: '2026-12-20',
      hasta: '2027-01-30',
    })
    expect(fechaSugerida('2026-12-20', '2026-12-31')).toBe('2027-01-25')
  })

  it.each(['2026-09-28', '2026-11-05'])(
    'fecha de seguimiento %s fuera del rango → mensaje con el rango en dd/mm/aaaa',
    (fecha) => {
      expect(validarFechaSeguimiento(fecha, HOY, '2026-10-05')).toBe(
        'La fecha de seguimiento debe estar entre el 29/09/2026 y el 04/11/2026.',
      )
    },
  )

  it.each([HOY, '2026-11-04', '2026-10-30'])('fecha de seguimiento %s (extremos incluidos) → valida', (fecha) => {
    expect(validarFechaSeguimiento(fecha, HOY, '2026-10-05')).toBeNull()
  })

  it('fecha de seguimiento vacia o invalida → mensaje propio', () => {
    expect(validarFechaSeguimiento('', HOY, '2026-10-05')).toBe('Indique la fecha de seguimiento.')
    expect(validarFechaSeguimiento('2026-02-30', HOY, '2026-10-05')).toBe(
      'Ingrese una fecha válida (AAAA-MM-DD).',
    )
  })

  it('fechaLocalIso usa la fecha local del navegador', () => {
    expect(fechaLocalIso(new Date(2026, 8, 29, 23, 30))).toBe('2026-09-29')
    expect(fechaLocalIso(new Date(2026, 0, 5, 0, 1))).toBe('2026-01-05')
  })
})

describe('reglasGestion: opcionesPermitidas', () => {
  it('sin campaña → ofrecida y aceptada solo "No aplica" (aunque se haya contactado)', () => {
    expect(opcionesPermitidas({ conCampania: false, contactado: true, ofrecida: null })).toEqual({
      ofrecida: ['NO_APLICA'],
      aceptada: ['NO_APLICA'],
    })
  })

  it('con campaña y no contactado → ofrecida y aceptada solo "No aplica"', () => {
    expect(opcionesPermitidas({ conCampania: true, contactado: false, ofrecida: null })).toEqual({
      ofrecida: ['NO_APLICA'],
      aceptada: ['NO_APLICA'],
    })
  })

  it('con campaña y contactado: ofrecida Sí/No; ofrecida No → aceptada solo "No aplica"', () => {
    expect(opcionesPermitidas({ conCampania: true, contactado: true, ofrecida: 'NO' })).toEqual({
      ofrecida: ['SI', 'NO'],
      aceptada: ['NO_APLICA'],
    })
  })

  it('ofrecida Sí → aceptada Sí/No/Pendiente', () => {
    expect(opcionesPermitidas({ conCampania: true, contactado: true, ofrecida: 'SI' })).toEqual({
      ofrecida: ['SI', 'NO'],
      aceptada: ['SI', 'NO', 'PENDIENTE'],
    })
  })

  it('con campaña y sin responder si se contacto → nada elegible todavia', () => {
    expect(opcionesPermitidas({ conCampania: true, contactado: null, ofrecida: null })).toEqual({
      ofrecida: [],
      aceptada: [],
    })
  })

  it('ajustarRespuestas: al pasar a no contactado quedan en "No aplica"; una sola opcion se elige sola', () => {
    expect(
      ajustarRespuestas(true, { contactado: false, ofrecida: 'SI', aceptada: 'SI' }),
    ).toEqual({ contactado: false, ofrecida: 'NO_APLICA', aceptada: 'NO_APLICA' })
    expect(
      ajustarRespuestas(true, { contactado: true, ofrecida: 'NO_APLICA', aceptada: 'NO_APLICA' }),
    ).toEqual({ contactado: true, ofrecida: null, aceptada: null })
    expect(ajustarRespuestas(true, { contactado: true, ofrecida: 'NO', aceptada: 'SI' })).toEqual({
      contactado: true,
      ofrecida: 'NO',
      aceptada: 'NO_APLICA',
    })
    expect(ajustarRespuestas(true, { contactado: true, ofrecida: 'SI', aceptada: 'PENDIENTE' })).toEqual(
      { contactado: true, ofrecida: 'SI', aceptada: 'PENDIENTE' },
    )
  })
})

describe('reglasGestion: validarResultado (filas de coherencia de la decision (h))', () => {
  const CONTEXTO: ContextoResultado = {
    conCampania: true,
    fechaAsignacion: '2026-09-20',
    hoy: HOY,
    vencimiento: '2026-10-05',
    fechaSeguimientoActual: '2026-10-25',
  }
  const BASE: BorradorResultado = {
    contactado: true,
    campaniaOfrecida: 'SI',
    campaniaAceptada: 'SI',
    renovoDeclarado: 'SI',
    fechaContacto: '2026-09-25',
    observaciones: '',
    responsable: '',
    fechaSeguimiento: '2026-10-25',
  }

  it.each<[string, Partial<BorradorResultado>, Partial<ContextoResultado>, string, string]>([
    ['no contactado + ofrecida Sí', { contactado: false, fechaContacto: '' }, {}, 'campaniaOfrecida', 'Si no se contactó al socio, la oferta y la aceptación deben ser «No aplica».'],
    ['sin campaña + ofrecida No', { campaniaOfrecida: 'NO', campaniaAceptada: 'NO_APLICA' }, { conCampania: false }, 'campaniaOfrecida', 'Sin campaña asignada, la oferta y la aceptación deben ser «No aplica».'],
    ['contactado + ofrecida No + aceptada Sí', { campaniaOfrecida: 'NO', campaniaAceptada: 'SI' }, {}, 'campaniaAceptada', 'Si no se ofreció la campaña, la aceptación debe ser «No aplica».'],
    ['contactado + ofrecida Sí + aceptada No aplica', { campaniaAceptada: 'NO_APLICA' }, {}, 'campaniaAceptada', 'Indique si el socio aceptó la campaña (Sí, No o Pendiente).'],
    ['contactado + ofrecida No aplica', { campaniaOfrecida: 'NO_APLICA', campaniaAceptada: 'NO_APLICA' }, {}, 'campaniaOfrecida', 'Indique si se ofreció la campaña (Sí o No).'],
    ['contactado sin fecha de contacto', { fechaContacto: '' }, {}, 'fechaContacto', 'Indique la fecha del contacto.'],
    ['fecha de contacto futura', { fechaContacto: '2026-09-30' }, {}, 'fechaContacto', 'La fecha del contacto debe estar entre el 20/09/2026 y el 29/09/2026.'],
    ['fecha de contacto anterior a la asignacion', { fechaContacto: '2026-09-19' }, {}, 'fechaContacto', 'La fecha del contacto debe estar entre el 20/09/2026 y el 29/09/2026.'],
    ['no contactado con fecha de contacto', { contactado: false, campaniaOfrecida: 'NO_APLICA', campaniaAceptada: 'NO_APLICA' }, {}, 'fechaContacto', 'Si no se contactó al socio, no indique la fecha del contacto.'],
    ['sin responder si se contacto', { contactado: null }, {}, 'contactado', 'Indique si se contactó al socio.'],
    ['sin responder si renovo', { renovoDeclarado: null }, {}, 'renovoDeclarado', 'Indique si el socio renovó.'],
    ['renovo Pendiente con nueva fecha de seguimiento fuera del rango', { renovoDeclarado: 'PENDIENTE', fechaSeguimiento: '2026-11-05' }, {}, 'fechaSeguimiento', 'La fecha de seguimiento debe estar entre el 29/09/2026 y el 04/11/2026.'],
  ])('%s → error', (_caso, cambios, contexto, campo, mensaje) => {
    const resultado = validarResultado({ ...BASE, ...cambios }, { ...CONTEXTO, ...contexto })

    expect(resultado.params).toBeNull()
    expect(resultado.errores?.[campo as keyof typeof resultado.errores]).toBe(mensaje)
  })

  it.each<[string, Partial<BorradorResultado>, Partial<ContextoResultado>]>([
    ['sin campaña, no contactado', { contactado: false, campaniaOfrecida: 'NO_APLICA', campaniaAceptada: 'NO_APLICA', fechaContacto: '' }, { conCampania: false }],
    ['sin campaña, contactado', { campaniaOfrecida: 'NO_APLICA', campaniaAceptada: 'NO_APLICA' }, { conCampania: false }],
    ['con campaña, no contactado', { contactado: false, campaniaOfrecida: 'NO_APLICA', campaniaAceptada: 'NO_APLICA', fechaContacto: '' }, {}],
    ['ofrecida No, aceptada No aplica', { campaniaOfrecida: 'NO', campaniaAceptada: 'NO_APLICA' }, {}],
    ['ofrecida Sí, aceptada Sí', {}, {}],
    ['ofrecida Sí, aceptada No', { campaniaAceptada: 'NO' }, {}],
    ['ofrecida Sí, aceptada Pendiente', { campaniaAceptada: 'PENDIENTE' }, {}],
    ['fecha de contacto = asignacion', { fechaContacto: '2026-09-20' }, {}],
    ['fecha de contacto = hoy', { fechaContacto: HOY }, {}],
  ])('%s → coherente', (_caso, cambios, contexto) => {
    expect(validarResultado({ ...BASE, ...cambios }, { ...CONTEXTO, ...contexto }).errores).toBeNull()
  })

  it('params: textos recortados (vacios → null); sin fecha de contacto si no se contacto', () => {
    const resultado = validarResultado(
      {
        ...BASE,
        contactado: false,
        campaniaOfrecida: 'NO_APLICA',
        campaniaAceptada: 'NO_APLICA',
        renovoDeclarado: 'NO',
        fechaContacto: '',
        observaciones: '  No contesta  ',
        responsable: '   ',
      },
      CONTEXTO,
    )

    expect(resultado.params).toEqual({
      contactado: false,
      campaniaOfrecida: 'NO_APLICA',
      campaniaAceptada: 'NO_APLICA',
      renovoDeclarado: 'NO',
      fechaContacto: null,
      observaciones: 'No contesta',
      responsable: null,
      fechaSeguimiento: null,
    })
  })

  it('fecha de seguimiento: solo viaja si Renovó = Pendiente y cambio (sin cambio → null, se conserva)', () => {
    const pendiente = { ...BASE, renovoDeclarado: 'PENDIENTE' as const }
    expect(validarResultado(pendiente, CONTEXTO).params?.fechaSeguimiento).toBeNull()
    expect(
      validarResultado({ ...pendiente, fechaSeguimiento: '2026-11-01' }, CONTEXTO).params
        ?.fechaSeguimiento,
    ).toBe('2026-11-01')
    // Renovó = Sí cierra la gestion: la fecha de seguimiento no se envia aunque haya cambiado.
    expect(
      validarResultado({ ...BASE, fechaSeguimiento: '2026-11-01' }, CONTEXTO).params
        ?.fechaSeguimiento,
    ).toBeNull()
  })

  it('MENSAJE_FECHA_CONTACTO es el del formulario', () => {
    expect(MENSAJE_FECHA_CONTACTO).toBe('Indique la fecha del contacto.')
  })

  it('funciones puras: no leen el reloj ni llaman a la API', () => {
    expect(source).not.toMatch(/new Date\(\)|Date\.now|from\s+['"][^'"]*\/api\//)
  })
})
