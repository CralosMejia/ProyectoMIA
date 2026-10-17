import { expect, type Locator, type Page, test } from '@playwright/test'
import { crearPlantillaSintetica } from './plantilla-sintetica'

/**
 * Recorrido critico del Dia 6 (R-011/T29): alertas de seguimiento (CU-09) y dashboard del mes
 * (CU-11).
 *
 * Generar lista -> gestionar un socio con campaña y seguimiento HOY -> Inicio «Para hoy» sube en 1
 * -> pulsarlo -> la fila esta en Seguimiento -> «Abrir gestión» -> registrar «¿Renovó? Sí» -> la
 * fila desaparece y el contador vuelve -> Dashboard del mes con la campaña (1 gestion, «Casos
 * insuficientes») y la tarjeta «Versión vN» del modelo vigente (R-015: ya no siempre v1).
 * R-012: la ventana se cierra al crear con campaña; ayuda de Inicio y del Dashboard; «Resultados de
 * <mes>», embudo y dona (la gestion suma 1 a «Renovaron» y al total respecto de antes de crearla) e
 * «Imprimir / Guardar PDF», que llama a window.print (sustituido: no se abre el dialogo real).
 *
 * CREA una campaña, una carga, una lista y una gestion: se ejecuta SOLO contra el stack aislado
 * `mtabolic-e2e` (E2E_BASE_URL=http://localhost:8081), nunca contra el principal.
 * Solo datos ficticios (plantilla sintetica). La fila de Seguimiento se identifica por el nombre
 * unico de la campaña creada en esta ejecucion, no por el socio. En la Lista se toma la ULTIMA
 * fila sin gestion (campanias-gestion toma la primera) para no competir por el mismo
 * ciclo si los specs corren en paralelo; los contadores son globales, asi que la ejecucion de
 * referencia es con `--workers=1`.
 */

const PUERTO_PRINCIPAL = ':8080'
const NIVELES = ['Alto', 'Medio', 'Bajo'] as const
const PLANES = ['Mensual', 'Trimestral', 'Semestral', 'Anual', 'Otro'] as const

/** Fecha de hoy en el calendario local, `YYYY-MM-DD` (la misma que usa la pantalla). */
function hoyLocal(): string {
  const d = new Date()
  const dos = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`
}

function grupo(contenedor: Locator, leyenda: string): Locator {
  return contenedor.getByRole('group', { name: leyenda })
}

function enlaceParaHoy(page: Page): Locator {
  return page.getByRole('link', { name: /^Para hoy \d+$/ })
}

/** Abre Inicio y devuelve el contador «Para hoy» que muestra la pantalla. */
async function leerParaHoy(page: Page): Promise<number> {
  await page.goto('/')
  const enlace = enlaceParaHoy(page)
  await expect(enlace).toBeVisible({ timeout: 30_000 })
  const numero = /(\d+)\s*$/.exec(((await enlace.textContent()) ?? '').trim())
  expect(numero).not.toBeNull()
  return Number(numero?.[1])
}

const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'septiembre',
  'octubre',
  'noviembre',
  'diciembre',
] as const

/** "2026-09-30" -> "septiembre de 2026" (independiente de la zona del navegador). */
function mesEnPalabras(fecha: string): string {
  const [anio, mes] = fecha.split('-')
  return `${MESES[Number(mes) - 1]} de ${anio}`
}

interface Dona {
  renovaron: number
  noRenovaron: number
  sinResultado: number
  total: number
}

function graficoResultados(page: Page): Locator {
  return page.getByRole('img', { name: /^Resultado de las gestiones del mes:/ })
}

/**
 * Abre el Dashboard del mes actual y lee las cifras de la dona desde su texto accesible.
 * Si el mes aun no tiene gestiones, la pagina no dibuja graficos: todo 0.
 */
async function leerDona(page: Page): Promise<Dona> {
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible()
  const grafico = graficoResultados(page)
  const vacio = page.getByText('No hay gestiones asignadas en este mes')
  await expect(grafico.or(vacio)).toBeVisible({ timeout: 30_000 })
  if (await vacio.isVisible()) return { renovaron: 0, noRenovaron: 0, sinResultado: 0, total: 0 }
  const texto = (await grafico.getAttribute('aria-label')) ?? ''
  const cifra = (patron: RegExp) => {
    const m = patron.exec(texto)
    expect(m, `"${patron.source}" en el texto accesible del grafico`).not.toBeNull()
    return Number(m?.[1])
  }
  return {
    renovaron: cifra(/: renovaron (\d+) /),
    noRenovaron: cifra(/no renovaron (\d+) /),
    sinResultado: cifra(/sin resultado (\d+) /),
    total: cifra(/total (\d+)$/),
  }
}

async function cargarPlantilla(page: Page, ruta: string) {
  await page.goto('/carga')
  await page.getByLabel('Archivo de la plantilla (.xlsx)').setInputFiles(ruta)
  await page.getByRole('button', { name: 'Revisar archivo' }).click()
  await expect(page.getByRole('region', { name: 'Vista previa' })).toBeVisible({ timeout: 30_000 })
  await page.getByRole('button', { name: 'Confirmar carga' }).click()
  await expect(page.getByRole('region', { name: 'Carga guardada' })).toBeVisible({
    timeout: 30_000,
  })
}

test('alertas para hoy: registrar el resultado desde Seguimiento y verlo en el Dashboard del mes', async ({
  page,
  baseURL,
}) => {
  test.skip(
    !baseURL || baseURL.includes(PUERTO_PRINCIPAL),
    'Crea campaña, carga, lista y gestion: solo contra el stack E2E aislado (E2E_BASE_URL=http://localhost:8081).',
  )
  test.setTimeout(180_000)

  const nombreCampania = `Campaña Alertas E2E ${Date.now()}`
  const hoy = hoyLocal()
  // R-015: la version vigente cambia con `adoptar-modelo`; se toma de /sistema/estado.
  const estado = await page.request.get('/api/v1/sistema/estado')
  expect(estado.status()).toBe(200)
  const versionVigente: string = (await estado.json()).modelo_vigente.version
  expect(versionVigente).toMatch(/^v\d+$/)

  await test.step('crear una campaña propia (todos los niveles y planes, prioridad 1)', async () => {
    await page.goto('/campanias')
    await expect(page.getByRole('heading', { level: 1, name: 'Campañas' })).toBeVisible()
    await page.getByRole('button', { name: 'Nueva campaña' }).click()
    const dialogo = page.getByRole('dialog', { name: 'Nueva campaña' })
    await dialogo.getByLabel('Nombre').fill(nombreCampania)
    // R-015 (M01): los niveles salen de cortes fijos (0,70/0,50), no de percentiles; con la
    // plantilla sintetica la lista puede no tener ningun Alto/Medio, asi que la campaña cubre
    // los tres niveles y la fila elegida (de cualquier nivel) siempre la tiene sugerida.
    for (const nivel of NIVELES) await grupo(dialogo, 'Niveles de riesgo').getByLabel(nivel).check()
    for (const plan of PLANES) await grupo(dialogo, 'Planes').getByLabel(plan).check()
    await dialogo.getByLabel('Prioridad').fill('1')
    const creada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/campanias$/.test(r.url()),
    )
    await dialogo.getByRole('button', { name: 'Guardar' }).click()
    expect((await creada).status()).toBe(201)
    await expect(dialogo).toHaveCount(0)
  })

  await test.step('cargar socios ficticios y generar la lista', async () => {
    const plantilla = await crearPlantillaSintetica(test.info().outputPath('plantilla_alertas.xlsx'))
    await cargarPlantilla(page, plantilla.ruta)

    await page.goto('/lista')
    await expect(page.getByRole('heading', { level: 1, name: 'Lista priorizada' })).toBeVisible()
    const creada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/listas$/.test(r.url()),
    )
    await page.getByRole('button', { name: 'Generar lista' }).click()
    expect((await creada).status()).toBe(201)
    await expect(page.getByRole('columnheader', { name: 'Gestión' }).first()).toBeVisible({
      timeout: 30_000,
    })
  })

  const paraHoyAntes = await test.step('Inicio: leer «Para hoy» antes de gestionar', async () =>
    leerParaHoy(page),
  )

  await test.step('Inicio: «¿Cómo funciona el inicio?» abre su ayuda y devuelve el foco al cerrar', async () => {
    const boton = page.getByRole('button', { name: '¿Cómo funciona el inicio?' })
    await boton.click()
    const ayuda = page.getByRole('dialog', { name: '¿Cómo funciona el inicio?' })
    await expect(ayuda).toBeVisible()
    for (const seccion of [
      'Seguimientos pendientes',
      'Qué hacer al pulsar un número',
      'Aviso de datos del mes',
    ]) {
      await expect(ayuda.getByRole('heading', { name: seccion, exact: true })).toBeVisible()
    }
    await ayuda.getByRole('button', { name: 'Cerrar' }).click()
    await expect(ayuda).toHaveCount(0)
    await expect(boton).toBeFocused()
  })

  const donaAntes = await test.step('Dashboard: leer el gráfico de resultados antes de gestionar', async () =>
    leerDona(page),
  )

  await test.step('gestionar un socio (cualquier nivel) con la campaña y seguimiento HOY', async () => {
    await page.goto('/lista')
    const fila = page
      .getByRole('row')
      .filter({ has: page.getByRole('button', { name: /^Gestionar prioridad \d+$/ }) })
      .filter({ has: page.getByText(/^(Alto|Medio|Bajo)$/) })
      .last()
    await expect(fila).toBeVisible({ timeout: 30_000 })
    await fila.getByRole('button', { name: /^Gestionar prioridad \d+$/ }).click()

    const dialogo = page.getByRole('dialog')
    const nueva = dialogo.getByRole('form', { name: 'Nueva gestión' })
    await expect(nueva).toBeVisible()
    await nueva.getByLabel(nombreCampania).check()
    await nueva.getByLabel('Fecha de seguimiento').fill(hoy)

    const creada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/gestiones$/.test(r.url()),
    )
    await nueva.getByRole('button', { name: 'Crear gestión' }).click()
    const respuesta = await creada
    expect(respuesta.status()).toBe(201)
    expect(respuesta.request().postDataJSON()).toMatchObject({ fecha_seguimiento: hoy })
    // R-012 (e): con exito la ventana se cierra sola; ya no pasa a «Resultado del seguimiento».
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(page.getByRole('form', { name: 'Resultado del seguimiento' })).toHaveCount(0)
  })

  await test.step('Inicio: «Para hoy» aumenta en 1', async () => {
    expect(await leerParaHoy(page)).toBe(paraHoyAntes + 1)
  })

  const filaSeguimiento = page
    .getByRole('row')
    .filter({ has: page.getByRole('cell', { name: nombreCampania, exact: true }) })

  await test.step('pulsar «Para hoy» lleva a Seguimiento y la fila de la gestion esta ahi', async () => {
    await enlaceParaHoy(page).click()
    await expect(page).toHaveURL(/\/seguimiento\?filtro=hoy$/)
    await expect(page.getByRole('heading', { level: 1, name: 'Seguimientos para hoy' })).toBeVisible()
    await expect(filaSeguimiento).toHaveCount(1)
  })

  await test.step('«Abrir gestión» y registrar ¿Renovó? Sí: la ventana se cierra y la fila desaparece', async () => {
    await filaSeguimiento.getByRole('button', { name: /^Abrir gestión / }).click()
    const dialogo = page.getByRole('dialog')
    const resultado = dialogo.getByRole('form', { name: 'Resultado del seguimiento' })
    await expect(resultado).toBeVisible()
    await expect(resultado.getByText(nombreCampania)).toBeVisible()
    await grupo(resultado, '¿Se contactó al socio?').getByLabel('Sí', { exact: true }).check()
    await grupo(resultado, '¿Se ofreció la campaña?').getByLabel('Sí', { exact: true }).check()
    await grupo(resultado, '¿Aceptó la campaña?').getByLabel('Sí', { exact: true }).check()
    await resultado.getByLabel('Fecha del contacto').fill(hoy)
    await grupo(resultado, '¿Renovó?').getByLabel('Sí', { exact: true }).check()

    const registrado = page.waitForResponse(
      (r) => r.request().method() === 'PUT' && /\/api\/v1\/gestiones\/\d+\/resultado$/.test(r.url()),
    )
    const recargada = page.waitForResponse(
      (r) => r.request().method() === 'GET' && /\/api\/v1\/gestiones\?filtro=hoy$/.test(r.url()),
    )
    await resultado.getByRole('button', { name: 'Guardar resultado' }).click()
    expect((await registrado).status()).toBe(200)
    expect((await recargada).status()).toBe(200)
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(filaSeguimiento).toHaveCount(0)
  })

  await test.step('Inicio: «Para hoy» vuelve al valor inicial', async () => {
    expect(await leerParaHoy(page)).toBe(paraHoyAntes)
  })

  const filaDashboard = page
    .getByRole('row')
    .filter({ has: page.getByRole('cell', { name: nombreCampania, exact: true }) })

  await test.step('Dashboard del mes: la campaña con 1 gestion, «Casos insuficientes» y «Versión» del modelo vigente', async () => {
    await page.goto('/dashboard')
    await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible()
    await expect(page.getByLabel('Mes', { exact: true })).toHaveValue(hoy.slice(0, 7))
    await expect(filaDashboard).toHaveCount(1, { timeout: 30_000 })
    // Columnas: Campaña · Gestiones · Contactados · Renovaron · Tasa de renovación
    const celdas = filaDashboard.getByRole('cell')
    await expect(celdas.nth(1)).toHaveText('1')
    await expect(celdas.nth(2)).toHaveText('1')
    await expect(celdas.nth(3)).toHaveText('1')
    await expect(celdas.nth(4)).toContainText('Casos insuficientes')
    await expect(page.getByText(`Versión ${versionVigente}`, { exact: true })).toBeVisible()
  })

  await test.step('Dashboard: «Resultados de <mes>», embudo y dona con la gestion contada como «Renovaron»', async () => {
    await expect(page.getByText(`Resultados de ${mesEnPalabras(hoy)}`, { exact: true })).toBeVisible()
    await expect(
      page.getByRole('heading', { level: 2, name: 'Avance de las gestiones con campaña' }),
    ).toBeVisible()
    await expect(page.getByRole('img', { name: /^Embudo del mes: / })).toBeVisible()
    await expect(
      page.getByRole('heading', { level: 2, name: 'Resultado de las gestiones del mes' }),
    ).toBeVisible()
    await expect(graficoResultados(page)).toBeVisible()
    await expect(page.getByRole('table', { name: 'Datos del gráfico de resultados' })).toBeVisible()

    const despues = await leerDona(page)
    expect(despues).toEqual({
      renovaron: donaAntes.renovaron + 1,
      noRenovaron: donaAntes.noRenovaron,
      sinResultado: donaAntes.sinResultado,
      total: donaAntes.total + 1,
    })
  })

  await test.step('Dashboard: «¿Cómo funciona el dashboard?» abre su ayuda y devuelve el foco al cerrar', async () => {
    const boton = page.getByRole('button', { name: '¿Cómo funciona el dashboard?' })
    await boton.click()
    const ayuda = page.getByRole('dialog', { name: '¿Cómo funciona el dashboard?' })
    await expect(ayuda).toBeVisible()
    await expect(ayuda.getByRole('heading', { name: 'El embudo', exact: true })).toBeVisible()
    await expect(
      ayuda.getByRole('heading', { name: 'Resultado de las gestiones', exact: true }),
    ).toBeVisible()
    await ayuda.getByRole('button', { name: 'Cerrar' }).click()
    await expect(ayuda).toHaveCount(0)
    await expect(boton).toBeFocused()
  })

  await test.step('Dashboard: «Imprimir / Guardar PDF» habilitado llama a window.print sin pedir nada a la API', async () => {
    // Se sustituye window.print para no abrir el dialogo real del navegador.
    await page.evaluate(() => {
      const w = window as unknown as { __impresiones: number; print: () => void }
      w.__impresiones = 0
      w.print = () => {
        w.__impresiones += 1
      }
    })
    const peticionesApi: string[] = []
    const anotar = (r: { url: () => string }) => {
      if (r.url().includes('/api/')) peticionesApi.push(r.url())
    }
    page.on('request', anotar)

    const imprimir = page.getByRole('button', { name: 'Imprimir / Guardar PDF' })
    await expect(imprimir).toBeEnabled()
    await imprimir.click()
    await expect
      .poll(() => page.evaluate(() => (window as unknown as { __impresiones: number }).__impresiones))
      .toBe(1)
    page.off('request', anotar)
    expect(peticionesApi).toEqual([])
    await expect(page.getByRole('dialog')).toHaveCount(0)
  })

  await test.step('Dashboard: filtrar por un mes sin gestiones pide ese mes y muestra el aviso', async () => {
    const pedido = page.waitForResponse(
      (r) => r.request().method() === 'GET' && /\/api\/v1\/dashboard\?mes=2000-01$/.test(r.url()),
    )
    await page.getByLabel('Mes', { exact: true }).fill('2000-01')
    expect((await pedido).status()).toBe(200)
    await expect(page.getByText('No hay gestiones asignadas en este mes')).toBeVisible()
    await expect(page.getByText('Resultados de enero de 2000', { exact: true })).toBeVisible()
    await expect(filaDashboard).toHaveCount(0)
    // Sin gestiones no se dibujan graficos.
    await expect(graficoResultados(page)).toHaveCount(0)
    await expect(page.getByRole('img', { name: /^Embudo del mes: / })).toHaveCount(0)
    await expect(page.getByText(`Versión ${versionVigente}`, { exact: true })).toBeVisible()
  })
})

// ------------------------------------------------------------------ R-018 (M04) · T8

type EstadoIndicador = 'COMPLETO' | 'PARCIAL' | 'PENDIENTE' | 'SIN_DATOS'

interface IndicadorApi {
  n: number
  estado: EstadoIndicador
  pendientes?: number
}

interface PilotoApi {
  estado: EstadoIndicador
  lista: { id: number; nombre: string; fecha_generacion: string } | null
  n_top: number
  precision_top25: IndicadorApi
  contactados_antes_vencimiento: IndicadorApi
  dias_anticipacion: IndicadorApi
  tasa_renovacion_contactados: IndicadorApi
  monto_retenido: IndicadorApi
}

/** Nombre visible de cada indicador (el mismo de la ayuda) y su bloque en la respuesta. */
const INDICADORES_PILOTO = [
  ['Precisión del top 25', 'precision_top25'],
  ['Contactados antes del vencimiento', 'contactados_antes_vencimiento'],
  ['Días de anticipación', 'dias_anticipacion'],
  ['Renovación de los contactados', 'tasa_renovacion_contactados'],
  ['Monto retenido', 'monto_retenido'],
] as const

const TEXTO_PENDIENTE =
  'Pendiente: aún no se puede verificar (se verifica 30 días después del vencimiento)'

/** Estado traducido que debe ver el usuario (nunca el nombre interno). */
function estadoVisible(estado: EstadoIndicador): string | RegExp {
  switch (estado) {
    case 'COMPLETO':
      return 'Completo'
    case 'PARCIAL':
      return /^Parcial/
    case 'PENDIENTE':
      return TEXTO_PENDIENTE
    case 'SIN_DATOS':
      return 'Sin datos'
  }
}

const CLAVES_PERSONALES = ['cedula', 'celular', 'correo', 'telefono', 'socio_id', 'membresia_id']

function claves(valor: unknown): string[] {
  if (Array.isArray(valor)) return valor.flatMap(claves)
  if (valor !== null && typeof valor === 'object')
    return Object.entries(valor).flatMap(([k, v]) => [k, ...claves(v)])
  return []
}

/** GET /dashboard?mes= por el stack: 200, con `piloto` y sin claves personales. */
async function leerPiloto(page: Page, mes: string): Promise<PilotoApi> {
  const respuesta = await page.request.get(`/api/v1/dashboard?mes=${mes}`)
  expect(respuesta.status()).toBe(200)
  const cuerpo: unknown = await respuesta.json()
  expect(claves(cuerpo).filter((k) => CLAVES_PERSONALES.includes(k))).toEqual([])
  const piloto = (cuerpo as { piloto?: PilotoApi }).piloto
  expect(piloto, '`piloto` en GET /dashboard').toBeDefined()
  // El unico `nombre` dentro de `piloto` es el de la lista (nunca el de un socio).
  const nombres = claves(piloto).filter((k) => k === 'nombre')
  expect(nombres.length).toBe(piloto?.lista ? 1 : 0)
  return piloto as PilotoApi
}

function seccionPiloto(page: Page): Locator {
  return page.getByRole('region', { name: 'Indicadores del piloto' })
}

function tarjetaIndicador(seccion: Locator, nombre: string): Locator {
  return seccion
    .locator('dl > div')
    .filter({ has: seccion.page().locator('dt').getByText(nombre, { exact: true }) })
}

/** Texto del `n` en pantalla: el del monto aclara que cuenta solo a los ya verificados. */
function textoN(nombre: string, n: number): string {
  return nombre === 'Monto retenido' ? `n = ${n} contactados ya verificados` : `n = ${n}`
}

/** Cada indicador de la pantalla con el `n` y el estado traducido de la respuesta. */
async function comprobarIndicadores(seccion: Locator, piloto: PilotoApi) {
  await expect(seccion.locator('dl > div')).toHaveCount(INDICADORES_PILOTO.length)
  for (const [nombre, clave] of INDICADORES_PILOTO) {
    const tarjeta = tarjetaIndicador(seccion, nombre)
    await expect(tarjeta, nombre).toHaveCount(1)
    await expect(tarjeta.getByText(textoN(nombre, piloto[clave].n), { exact: true }), nombre).toBeVisible()
    const estado = estadoVisible(piloto[clave].estado)
    await expect(
      typeof estado === 'string'
        ? tarjeta.getByText(estado, { exact: true })
        : tarjeta.getByText(estado),
      nombre,
    ).toBeVisible()
    // Nunca el nombre interno del estado.
    await expect(tarjeta.getByText(/^(COMPLETO|PARCIAL|PENDIENTE|SIN_DATOS)$/)).toHaveCount(0)
  }
}

test('indicadores del piloto: lista del mes pendiente, mes sin lista «Sin datos», impresión y ayuda', async ({
  page,
  baseURL,
}) => {
  test.skip(
    !baseURL || baseURL.includes(PUERTO_PRINCIPAL),
    'Puede generar una lista: solo contra el stack E2E aislado (E2E_BASE_URL=http://localhost:8081).',
  )
  test.setTimeout(180_000)
  const mes = hoyLocal().slice(0, 7)

  let piloto = await leerPiloto(page, mes)

  if (piloto.lista === null) {
    await test.step('el mes en curso aún no tiene lista: generarla', async () => {
      await page.goto('/lista')
      await expect(page.getByRole('heading', { level: 1, name: 'Lista priorizada' })).toBeVisible()
      const creada = page.waitForResponse(
        (r) => r.request().method() === 'POST' && /\/api\/v1\/listas$/.test(r.url()),
      )
      await page.getByRole('button', { name: 'Generar lista' }).click()
      expect((await creada).status()).toBe(201)
      piloto = await leerPiloto(page, mes)
    })
  }

  await test.step('API: la lista del mes en curso tiene top y su precisión aún no se puede verificar', async () => {
    expect(piloto.lista).not.toBeNull()
    expect(piloto.n_top).toBeGreaterThan(0)
    expect(piloto.n_top).toBeLessThanOrEqual(25)
    // Vencimientos >= dia de generacion (este mes) -> T + 30 > hoy >= corte: nadie verificado.
    expect(piloto.precision_top25.estado).toBe('PENDIENTE')
    expect(piloto.precision_top25.pendientes).toBe(piloto.precision_top25.n)
  })

  const seccion = seccionPiloto(page)

  await test.step('Dashboard: «Indicadores del piloto» con sus 5 indicadores, n y estado traducido', async () => {
    await page.goto('/dashboard')
    await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible()
    await expect(page.getByLabel('Mes', { exact: true })).toHaveValue(mes)
    await expect(seccion).toBeVisible({ timeout: 30_000 })
    await expect(
      seccion.getByRole('heading', { level: 2, name: 'Indicadores del piloto' }),
    ).toBeVisible()
    await expect(
      seccion.getByText(`Lista del mes: ${piloto.lista?.nombre}, generada el `),
    ).toBeVisible()
    await comprobarIndicadores(seccion, piloto)
    await expect(
      tarjetaIndicador(seccion, 'Precisión del top 25').getByText(TEXTO_PENDIENTE, {
        exact: true,
      }),
    ).toBeVisible()
    await expect(
      seccion.getByText(
        'Los socios del top 25 se contactan; por eso la precisión observada puede quedar por debajo de la real.',
      ),
    ).toBeVisible()
    await expect(seccion.getByText('Cifras observadas, no causales.')).toBeVisible()
  })

  await test.step('impresión: la sección no lleva print:hidden y se ve con el medio «print»', async () => {
    const oculta = await seccion.evaluate((el) => {
      for (let n: Element | null = el; n; n = n.parentElement) {
        if (n.classList.contains('print:hidden')) return true
      }
      return false
    })
    expect(oculta).toBe(false)
    await page.emulateMedia({ media: 'print' })
    await expect(seccion).toBeVisible()
    await expect(seccion.locator('dl > div')).toHaveCount(INDICADORES_PILOTO.length)
    for (const [nombre] of INDICADORES_PILOTO) {
      await expect(tarjetaIndicador(seccion, nombre)).toBeVisible()
    }
    // Lo que si se oculta al imprimir sigue oculto (el boton de imprimir).
    await expect(page.getByRole('button', { name: 'Imprimir / Guardar PDF' })).toBeHidden()
    await page.emulateMedia({ media: 'screen' })
  })

  await test.step('ayuda: sección «Indicadores del piloto» con los cinco, pendiente a los 30 días y sesgo', async () => {
    const boton = page.getByRole('button', { name: '¿Cómo funciona el dashboard?' })
    await boton.click()
    const ayuda = page.getByRole('dialog', { name: '¿Cómo funciona el dashboard?' })
    await expect(ayuda).toBeVisible()
    await expect(
      ayuda.getByRole('heading', { name: 'Indicadores del piloto', exact: true }),
    ).toBeVisible()
    // Una definicion (elemento de la lista) por indicador; el nombre tambien aparece citado
    // en otros parrafos de la seccion, por eso se busca el elemento que empieza por «nombre»:.
    for (const [nombre] of INDICADORES_PILOTO) {
      const definicion = ayuda.getByRole('listitem').filter({ hasText: `«${nombre}»:` })
      await expect(definicion, nombre).toHaveCount(1)
      await expect(definicion, nombre).toBeVisible()
    }
    await expect(
      ayuda.getByText(/«Monto retenido» cuenta solo a los contactados ya verificados/),
    ).toBeVisible()
    await expect(ayuda.getByText(/30 días después de que vence su\s+membresía/)).toBeVisible()
    await expect(ayuda.getByText(/la precisión puede salir más baja que la real/)).toBeVisible()
    await expect(ayuda.getByText(/no prueban que el sistema cause la renovación/)).toBeVisible()
    await ayuda.getByRole('button', { name: 'Cerrar' }).click()
    await expect(ayuda).toHaveCount(0)
    await expect(boton).toBeFocused()
  })

  await test.step('mes sin lista (2000-01): «Sin datos» y n = 0 en los cinco', async () => {
    const vacio = await leerPiloto(page, '2000-01')
    expect(vacio.estado).toBe('SIN_DATOS')
    expect(vacio.lista).toBeNull()
    const pedido = page.waitForResponse(
      (r) => r.request().method() === 'GET' && /\/api\/v1\/dashboard\?mes=2000-01$/.test(r.url()),
    )
    await page.getByLabel('Mes', { exact: true }).fill('2000-01')
    expect((await pedido).status()).toBe(200)
    await expect(seccion.getByText('No hay una lista generada en este mes.')).toBeVisible()
    await comprobarIndicadores(seccion, vacio)
    for (const [nombre] of INDICADORES_PILOTO) {
      const tarjeta = tarjetaIndicador(seccion, nombre)
      await expect(tarjeta.getByText('Sin datos', { exact: true })).toBeVisible()
      await expect(tarjeta.getByText(textoN(nombre, 0), { exact: true })).toBeVisible()
    }
    await expect(seccion.getByText('Pocos casos: léase con cuidado')).toHaveCount(0)
  })
})
