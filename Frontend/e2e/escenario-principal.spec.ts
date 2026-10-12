import { expect, type Locator, type Page, test } from '@playwright/test'
import { crearPlantillaSintetica } from './plantilla-sintetica'

/**
 * Escenario principal del Dia 7 (R-013/T9, D7-OP-03): carga -> lista -> gestion con campaña ->
 * registrar el resultado (cierre) -> dashboard del mes.
 *
 * Plantilla sintetica con cedulas unicas por ejecucion -> «Revisar archivo» -> «Confirmar carga»
 * -> «Generar lista» con la fecha de hoy -> «Gestionar prioridad N» de UNO DE LOS SOCIOS RECIEN
 * CARGADOS con una campaña propia (todos los niveles y planes, para que se sugiera sea cual sea el
 * nivel) y fecha de seguimiento -> la fila muestra «Pendiente» -> «Registrar resultado prioridad N»
 * -> Renovó Sí -> la fila muestra «Cerrada» -> Dashboard del mes: el embudo suma 1 en «asignadas» y
 * en «renovaron», la dona suma 1 en «Renovaron», y la fila de la campaña tiene 1 gestion renovada.
 *
 * Ademas comprueba que ninguna pagina recorrida produce violaciones de la CSP (consola y evento
 * `securitypolicyviolation`).
 *
 * CREA una campaña, una carga, una lista y una gestion: se ejecuta SOLO contra el stack aislado
 * `mtabolic-e2e` (E2E_BASE_URL=http://localhost:8081), nunca contra el principal. Repetible sobre la
 * misma base: nombres y cedulas unicos por ejecucion y comparaciones relativas (antes/despues).
 * Los contadores del dashboard son globales: la ejecucion de referencia es con `--workers=1`.
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

/** Hoy + `dias` en el calendario local, `YYYY-MM-DD`. */
function hoyMasLocal(dias: number): string {
  const d = new Date()
  d.setDate(d.getDate() + dias)
  const dos = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`
}

function grupo(contenedor: Locator, leyenda: string): Locator {
  return contenedor.getByRole('group', { name: leyenda })
}

interface Embudo {
  asignadas: number
  contactadas: number
  ofrecidas: number
  aceptadas: number
  renovaron: number
}

interface Dona {
  renovaron: number
  noRenovaron: number
  sinResultado: number
  total: number
}

interface CifrasDashboard {
  embudo: Embudo
  dona: Dona
}

const SIN_GESTIONES: CifrasDashboard = {
  embudo: { asignadas: 0, contactadas: 0, ofrecidas: 0, aceptadas: 0, renovaron: 0 },
  dona: { renovaron: 0, noRenovaron: 0, sinResultado: 0, total: 0 },
}

function cifra(texto: string, patron: RegExp): number {
  const m = patron.exec(texto)
  expect(m, `"${patron.source}" en "${texto}"`).not.toBeNull()
  return Number(m?.[1])
}

/** Abre el Dashboard del mes actual y lee embudo y dona de su texto accesible (0 si no hay datos). */
async function leerDashboard(page: Page): Promise<CifrasDashboard> {
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible()
  const embudo = page.getByRole('img', { name: /^Embudo del mes: / })
  const dona = page.getByRole('img', { name: /^Resultado de las gestiones del mes:/ })
  const vacio = page.getByText('No hay gestiones asignadas en este mes')
  await expect(embudo.or(vacio)).toBeVisible({ timeout: 30_000 })
  if (await vacio.isVisible()) return SIN_GESTIONES
  const textoEmbudo = (await embudo.getAttribute('aria-label')) ?? ''
  const textoDona = (await dona.getAttribute('aria-label')) ?? ''
  return {
    embudo: {
      asignadas: cifra(textoEmbudo, /asignadas (\d+)/),
      contactadas: cifra(textoEmbudo, /contactadas (\d+)/),
      ofrecidas: cifra(textoEmbudo, /ofrecidas (\d+)/),
      aceptadas: cifra(textoEmbudo, /aceptadas (\d+)/),
      renovaron: cifra(textoEmbudo, /renovaron (\d+)/),
    },
    dona: {
      renovaron: cifra(textoDona, /: renovaron (\d+) /),
      noRenovaron: cifra(textoDona, /no renovaron (\d+) /),
      sinResultado: cifra(textoDona, /sin resultado (\d+) /),
      total: cifra(textoDona, /total (\d+)$/),
    },
  }
}

test('escenario principal: carga, lista, gestion con campaña, resultado y dashboard del mes', async ({
  page,
  baseURL,
}) => {
  test.skip(
    !baseURL || baseURL.includes(PUERTO_PRINCIPAL),
    'Crea campaña, carga, lista y gestion: solo contra el stack E2E aislado (E2E_BASE_URL=http://localhost:8081).',
  )
  test.setTimeout(180_000)

  // Vigilancia de la CSP durante todo el recorrido.
  const violacionesCsp: string[] = []
  page.on('console', (mensaje) => {
    const texto = mensaje.text()
    if (/Content Security Policy|Refused to (load|execute|apply|connect|frame)/i.test(texto)) {
      violacionesCsp.push(texto)
    }
  })
  await page.addInitScript(() => {
    document.addEventListener('securitypolicyviolation', (e) => {
      console.error(`Content Security Policy violation: ${e.violatedDirective} ${e.blockedURI}`)
    })
  })

  const nombreCampania = `Campaña Escenario E2E ${Date.now()}`
  const hoy = hoyLocal()
  const seguimiento = hoyMasLocal(3)

  await test.step('crear una campaña propia (todos los niveles y planes, prioridad 1)', async () => {
    await page.goto('/campanias')
    await expect(page.getByRole('heading', { level: 1, name: 'Campañas' })).toBeVisible()
    await page.getByRole('button', { name: 'Nueva campaña' }).click()
    const dialogo = page.getByRole('dialog', { name: 'Nueva campaña' })
    await dialogo.getByLabel('Nombre').fill(nombreCampania)
    for (const nivel of NIVELES) await grupo(dialogo, 'Niveles de riesgo').getByLabel(nivel).check()
    for (const plan of PLANES) await grupo(dialogo, 'Planes').getByLabel(plan).check()
    await dialogo.getByLabel('Prioridad').fill('1')
    const creada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/campanias$/.test(r.url()),
    )
    await dialogo.getByRole('button', { name: 'Guardar' }).click()
    expect((await creada).status()).toBe(201)
    await expect(dialogo).toHaveCount(0)
    await expect(page.getByRole('cell', { name: nombreCampania, exact: true })).toBeVisible()
  })

  const antes = await test.step('Dashboard: leer embudo y dona antes de gestionar', async () =>
    leerDashboard(page),
  )

  const plantilla = await test.step('carga: «Revisar archivo» y «Confirmar carga»', async () => {
    const generada = await crearPlantillaSintetica(
      test.info().outputPath('plantilla_escenario.xlsx'),
    )
    await page.goto('/carga')
    await expect(page.getByRole('heading', { level: 1, name: 'Carga de datos' })).toBeVisible()
    await page.getByLabel('Archivo de la plantilla (.xlsx)').setInputFiles(generada.ruta)
    await page.getByRole('button', { name: 'Revisar archivo' }).click()
    await expect(page.getByRole('region', { name: 'Vista previa' })).toBeVisible({
      timeout: 30_000,
    })
    const confirmada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/cargas$/.test(r.url()),
    )
    await page.getByRole('button', { name: 'Confirmar carga' }).click()
    expect((await confirmada).status()).toBe(201)
    await expect(page.getByRole('region', { name: 'Carga guardada' })).toBeVisible({
      timeout: 30_000,
    })
    return generada
  })

  await test.step('lista: «Generar lista» con la fecha de hoy incluye a los socios cargados', async () => {
    await page.goto('/lista')
    await expect(page.getByRole('heading', { level: 1, name: 'Lista priorizada' })).toBeVisible()
    const creada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/listas$/.test(r.url()),
    )
    await page.getByRole('button', { name: 'Generar lista' }).click()
    const respuesta = await creada
    expect(respuesta.status()).toBe(201)
    expect(await respuesta.json()).toMatchObject({ fecha_generacion: hoy })
    await expect(page.getByRole('columnheader', { name: 'Gestión' }).first()).toBeVisible({
      timeout: 30_000,
    })
    const cedulas = plantilla.socios.map((s) => s.cedula)
    await expect(
      page.getByRole('cell', { name: new RegExp(`^(${cedulas.join('|')})$`) }).first(),
    ).toBeVisible()
  })

  const cedulas = plantilla.socios.map((s) => s.cedula)
  const prioridad = await test.step('«Gestionar prioridad N» en un socio recién cargado', async () => {
    const fila = page
      .getByRole('row')
      .filter({ has: page.getByRole('cell', { name: new RegExp(`^(${cedulas.join('|')})$`) }) })
      .filter({ has: page.getByRole('button', { name: /^Gestionar prioridad \d+$/ }) })
      .first()
    await expect(fila).toBeVisible()
    const boton = fila.getByRole('button', { name: /^Gestionar prioridad \d+$/ })
    const etiqueta = (await boton.getAttribute('aria-label')) ?? ''
    await boton.click()
    return etiqueta.replace('Gestionar prioridad ', '')
  })

  const dialogo = page.getByRole('dialog', { name: `Gestión de la prioridad ${prioridad}` })
  const fila = page.getByRole('row').filter({
    has: page.getByRole('button', { name: new RegExp(`prioridad ${prioridad}$`) }),
  })

  await test.step('crear la gestion con la campaña y fecha de seguimiento: la ventana se cierra', async () => {
    const nueva = dialogo.getByRole('form', { name: 'Nueva gestión' })
    await expect(nueva).toBeVisible()
    await nueva.getByLabel(nombreCampania).check()
    await nueva.getByLabel('Fecha de seguimiento').fill(seguimiento)
    const creada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/gestiones$/.test(r.url()),
    )
    await nueva.getByRole('button', { name: 'Crear gestión' }).click()
    const respuesta = await creada
    expect(respuesta.status()).toBe(201)
    expect(respuesta.request().postDataJSON()).toMatchObject({ fecha_seguimiento: seguimiento })
    await expect(dialogo).toHaveCount(0)
  })

  await test.step('la fila muestra «Pendiente» con la campaña', async () => {
    await expect(fila.getByRole('cell', { name: 'Pendiente', exact: true })).toBeVisible({
      timeout: 30_000,
    })
    await expect(fila.getByRole('cell', { name: nombreCampania, exact: true })).toBeVisible()
  })

  await test.step('«Registrar resultado prioridad N» con Renovó Sí: la ventana se cierra', async () => {
    await fila
      .getByRole('button', { name: `Registrar resultado prioridad ${prioridad}`, exact: true })
      .click()
    const resultado = dialogo.getByRole('form', { name: 'Resultado del seguimiento' })
    await expect(resultado).toBeVisible()
    await grupo(resultado, '¿Se contactó al socio?').getByLabel('Sí', { exact: true }).check()
    await grupo(resultado, '¿Se ofreció la campaña?').getByLabel('Sí', { exact: true }).check()
    await grupo(resultado, '¿Aceptó la campaña?').getByLabel('Sí', { exact: true }).check()
    await resultado.getByLabel('Fecha del contacto').fill(hoy)
    await grupo(resultado, '¿Renovó?').getByLabel('Sí', { exact: true }).check()
    const registrado = page.waitForResponse(
      (r) => r.request().method() === 'PUT' && /\/api\/v1\/gestiones\/\d+\/resultado$/.test(r.url()),
    )
    await resultado.getByRole('button', { name: 'Guardar resultado' }).click()
    expect((await registrado).status()).toBe(200)
    await expect(dialogo).toHaveCount(0)
  })

  await test.step('la fila muestra «Cerrada»', async () => {
    await expect(fila.getByRole('cell', { name: 'Cerrada', exact: true })).toBeVisible({
      timeout: 30_000,
    })
    await expect(
      fila.getByRole('button', { name: `Registrar resultado prioridad ${prioridad}` }),
    ).toHaveCount(0)
  })

  await test.step('Dashboard del mes: la gestion cuenta en el embudo y en «Renovaron»', async () => {
    const despues = await leerDashboard(page)
    await expect(page.getByLabel('Mes', { exact: true })).toHaveValue(hoy.slice(0, 7))
    expect(despues.embudo).toEqual({
      asignadas: antes.embudo.asignadas + 1,
      contactadas: antes.embudo.contactadas + 1,
      ofrecidas: antes.embudo.ofrecidas + 1,
      aceptadas: antes.embudo.aceptadas + 1,
      renovaron: antes.embudo.renovaron + 1,
    })
    expect(despues.dona).toEqual({
      renovaron: antes.dona.renovaron + 1,
      noRenovaron: antes.dona.noRenovaron,
      sinResultado: antes.dona.sinResultado,
      total: antes.dona.total + 1,
    })
    const filaCampania = page
      .getByRole('row')
      .filter({ has: page.getByRole('cell', { name: nombreCampania, exact: true }) })
    await expect(filaCampania).toHaveCount(1)
    // Columnas: Campaña · Gestiones · Contactados · Renovaron · Tasa de renovación
    const celdas = filaCampania.getByRole('cell')
    await expect(celdas.nth(1)).toHaveText('1')
    await expect(celdas.nth(3)).toHaveText('1')
  })

  await test.step('Inicio, Seguimiento y Salud cargan sin violaciones de la CSP', async () => {
    for (const ruta of ['/', '/seguimiento?filtro=hoy', '/salud']) {
      await page.goto(ruta)
      await page.waitForLoadState('networkidle')
    }
    expect(violacionesCsp).toEqual([])
  })
})
