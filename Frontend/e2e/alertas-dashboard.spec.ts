import { expect, type Locator, type Page, test } from '@playwright/test'
import { crearPlantillaSintetica } from './plantilla-sintetica'

/**
 * Recorrido critico del Dia 6 (R-011/T29): alertas de seguimiento (CU-09) y dashboard del mes
 * (CU-11).
 *
 * Generar lista -> gestionar un socio con campaña y seguimiento HOY -> Inicio «Para hoy» sube en 1
 * -> pulsarlo -> la fila esta en Seguimiento -> «Abrir gestión» -> registrar «¿Renovó? Sí» -> la
 * fila desaparece y el contador vuelve -> Dashboard del mes con la campaña (1 gestion, «Casos
 * insuficientes») y la tarjeta «Versión v1».
 * R-012: la ventana se cierra al crear con campaña; ayuda de Inicio y del Dashboard; «Resultados de
 * <mes>», embudo y dona (la gestion suma 1 a «Renovaron» y al total respecto de antes de crearla) e
 * «Imprimir / Guardar PDF», que llama a window.print (sustituido: no se abre el dialogo real).
 *
 * CREA una campaña, una carga, una lista y una gestion: se ejecuta SOLO contra el stack aislado
 * `mtabolic-e2e` (E2E_BASE_URL=http://localhost:8081), nunca contra el principal.
 * Solo datos ficticios (plantilla sintetica). La fila de Seguimiento se identifica por el nombre
 * unico de la campaña creada en esta ejecucion, no por el socio. En la Lista se toma la ULTIMA
 * fila Alto/Medio sin gestion (campanias-gestion toma la primera) para no competir por el mismo
 * ciclo si los specs corren en paralelo; los contadores son globales, asi que la ejecucion de
 * referencia es con `--workers=1`.
 */

const PUERTO_PRINCIPAL = ':8080'
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

  await test.step('crear una campaña propia (Alto/Medio, todos los planes, prioridad 1)', async () => {
    await page.goto('/campanias')
    await expect(page.getByRole('heading', { level: 1, name: 'Campañas' })).toBeVisible()
    await page.getByRole('button', { name: 'Nueva campaña' }).click()
    const dialogo = page.getByRole('dialog', { name: 'Nueva campaña' })
    await dialogo.getByLabel('Nombre').fill(nombreCampania)
    await grupo(dialogo, 'Niveles de riesgo').getByLabel('Alto').check()
    await grupo(dialogo, 'Niveles de riesgo').getByLabel('Medio').check()
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

  await test.step('gestionar un socio Alto/Medio con la campaña y seguimiento HOY', async () => {
    await page.goto('/lista')
    const fila = page
      .getByRole('row')
      .filter({ has: page.getByRole('button', { name: /^Gestionar prioridad \d+$/ }) })
      .filter({ has: page.getByText(/^(Alto|Medio)$/) })
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

  await test.step('Dashboard del mes: la campaña con 1 gestion, «Casos insuficientes» y «Versión v1»', async () => {
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
    await expect(page.getByText('Versión v1', { exact: true })).toBeVisible()
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
    await expect(page.getByText('Versión v1', { exact: true })).toBeVisible()
  })
})
