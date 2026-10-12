import { join } from 'node:path'
import ExcelJS from 'exceljs'
import { expect, type Locator, type Page, test } from '@playwright/test'
import { cedulasUnicas, TITULOS_REGISTROS } from './plantilla-sintetica'

/**
 * R-014/T5: las tablas no se recortan ni desbordan en escritorio y siguen siendo usables en movil.
 *
 * Prepara datos REALISTAS en el stack aislado (nombres de socio largos con tildes, planes y pagos
 * variados para que salgan varios motivos, una campaña de nombre y descripcion largos, una gestion
 * pendiente con responsable largo y otra cerrada sin campaña) y mide con datos reales del backend:
 *   - 1366x768 y 1920x1080: en /lista (las dos tablas), /seguimiento?filtro=proximas, /campanias y
 *     /dashboard, cada `table.scrollWidth <= contenedor.clientWidth` y la pagina sin desplazamiento
 *     horizontal (`documentElement.scrollWidth <= innerWidth`).
 *   - 390x844 en /lista: la pagina no desborda; el contenedor de la tabla tiene `overflow-x: auto`
 *     y, desplazado al final, el boton de accion de la primera fila queda dentro de la ventana.
 *   - Dashboard con `emulateMedia print` a 1366: cabecera oculta y tablas sin recorte.
 *
 * CREA campaña, carga, lista y gestiones: SOLO contra `mtabolic-e2e` (8081), nunca contra 8080.
 * Las medidas se adjuntan al informe (`medidas-*.json`) y se imprimen en la salida.
 * Capturas de /lista: en `E2E_CAPTURAS_DIR` si esta definida; si no, en la carpeta de salida.
 */

const PUERTO_PRINCIPAL = ':8080'
const NIVELES = ['Alto', 'Medio', 'Bajo'] as const
const PLANES = ['Mensual', 'Trimestral', 'Semestral', 'Anual', 'Otro'] as const
const MS_POR_DIA = 86_400_000

const ESCRITORIO = [
  { width: 1366, height: 768 },
  { width: 1920, height: 1080 },
] as const
const MOVIL = { width: 390, height: 844 }

const SELLO = Date.now()
const NOMBRE_CAMPANIA = `Campaña de reactivación para socios trimestrales con baja asistencia ${SELLO}`
const DESCRIPCION_CAMPANIA =
  'Llamada personalizada del entrenador asignado, sesión de evaluación física sin costo y ' +
  'descuento del 15 % en la renovación trimestral o semestral si el socio renueva antes del ' +
  'vencimiento; incluye seguimiento por WhatsApp a los tres días y recordatorio por correo.'
const RESPONSABLE = 'María José Villavicencio Santistevan (recepción turno de la tarde)'

/** Socios ficticios con nombres largos y realistas; plan, pago y asistencias variados. */
const SOCIOS = [
  { nombre: 'MARÍA FERNANDA DE LOS ÁNGELES VILLAVICENCIO SANTISTEVAN', plan: 'TRIMESTRAL', dias: 90, vence: 4, pago: 'EFECTIVO', asis: 1 },
  { nombre: 'JUAN CARLOS ALEJANDRO MONTENEGRO BUSTAMANTE', plan: 'MENSUAL', dias: 30, vence: 6, pago: 'TRANSFERENCIA', asis: 0 },
  { nombre: 'ANA LUCÍA DEL ROCÍO ZAMBRANO DE LA TORRE', plan: 'SEMESTRAL', dias: 180, vence: 8, pago: 'EFECTIVO', asis: 2 },
  { nombre: 'JOSÉ ANTONIO GUTIÉRREZ ECHEVERRÍA', plan: 'ANUAL', dias: 365, vence: 10, pago: 'TARJETA_DATAFAST', asis: 3 },
  { nombre: 'GABRIELA ALEJANDRA CHÁVEZ MALDONADO', plan: 'TRIMESTRAL', dias: 90, vence: 12, pago: 'TRANSFERENCIA', asis: 0 },
  { nombre: 'LUIS ENRIQUE QUIÑÓNEZ ARMIJOS', plan: 'MENSUAL', dias: 30, vence: 14, pago: 'EFECTIVO', asis: 1 },
  { nombre: 'VALENTINA MONSERRATH ESPINOZA CEVALLOS', plan: 'SEMESTRAL', dias: 180, vence: 16, pago: 'OTRO', asis: 0 },
  { nombre: 'FRANCISCO XAVIER BALSECA JARAMILLO', plan: 'TRIMESTRAL', dias: 90, vence: 18, pago: 'EFECTIVO', asis: 2 },
  { nombre: 'DIANA CAROLINA SOLÓRZANO VILLACRÉS', plan: 'MENSUAL', dias: 30, vence: 20, pago: 'TRANSFERENCIA', asis: 1 },
  { nombre: 'PEDRO PABLO ANDRADE MOSQUERA', plan: 'ANUAL', dias: 365, vence: 22, pago: 'EFECTIVO', asis: 0 },
] as const

const MONTO: Record<string, number> = { MENSUAL: 35, TRIMESTRAL: 95, SEMESTRAL: 180, ANUAL: 330 }

function hoyMasUtc(dias: number): Date {
  const a = new Date()
  return new Date(Date.UTC(a.getFullYear(), a.getMonth(), a.getDate()) + dias * MS_POR_DIA)
}

function hoyMasLocal(dias: number): string {
  const d = new Date()
  d.setDate(d.getDate() + dias)
  const dos = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`
}

/** Plantilla oficial con los socios de nombres largos (cedulas validas y unicas por ejecucion). */
async function crearPlantillaLarga(ruta: string): Promise<string[]> {
  const cedulas = cedulasUnicas(SOCIOS.length)
  const libro = new ExcelJS.Workbook()
  const hoja = libro.addWorksheet('Registros')
  hoja.addRow([...TITULOS_REGISTROS])
  SOCIOS.forEach((s, i) => {
    hoja.addRow([
      'NUEVO',
      s.nombre,
      cedulas[i],
      '',
      `socio.anchos.e2e.${i + 1}@example.com`,
      s.plan,
      hoyMasUtc(s.vence - s.dias),
      hoyMasUtc(s.vence),
      s.pago,
      '',
      MONTO[s.plan],
      MONTO[s.plan],
      s.asis,
      'Dato ficticio de prueba E2E (anchos de tabla)',
    ])
  })
  hoja.getColumn(7).numFmt = 'yyyy-mm-dd'
  hoja.getColumn(8).numFmt = 'yyyy-mm-dd'
  await libro.xlsx.writeFile(ruta)
  return cedulas
}

function grupo(contenedor: Locator, leyenda: string): Locator {
  return contenedor.getByRole('group', { name: leyenda })
}

interface MedidaTabla {
  caption: string
  tablaScrollWidth: number
  contenedorClientWidth: number
  /** Ancho minimo de la tabla sin desbordar (`min-content`): holgura = contenedor - este. */
  anchoMinimo: number
  columnas: Record<string, number>
}

interface Medidas {
  ruta: string
  viewport: string
  innerWidth: number
  documentoScrollWidth: number
  tablas: MedidaTabla[]
}

/** Mide cada `table` (scrollWidth frente al clientWidth de su contenedor) y la pagina. */
async function medir(page: Page, ruta: string): Promise<Medidas> {
  const datos = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    documentoScrollWidth: document.documentElement.scrollWidth,
    tablas: Array.from(document.querySelectorAll('table')).map((t) => ({
      caption: t.caption?.textContent?.trim() ?? '(sin caption)',
      tablaScrollWidth: t.scrollWidth,
      contenedorClientWidth: t.parentElement?.clientWidth ?? 0,
      anchoMinimo: (() => {
        // Solo medicion en la prueba: se restaura el estilo en la misma tarea.
        const previo = t.style.width
        t.style.width = 'min-content'
        const ancho = Math.ceil(t.getBoundingClientRect().width)
        t.style.width = previo
        return ancho
      })(),
      columnas: Object.fromEntries(
        Array.from(t.querySelectorAll('thead th')).map((th) => [
          th.textContent?.trim() ?? '',
          Math.round((th as HTMLElement).getBoundingClientRect().width),
        ]),
      ),
    })),
  }))
  const vp = page.viewportSize()
  const medidas: Medidas = { ruta, viewport: `${vp?.width}x${vp?.height}`, ...datos }
  const nombre = `medidas-${medidas.viewport}-${ruta.replace(/[^a-z0-9]+/gi, '_')}.json`
  await test.info().attach(nombre, {
    body: JSON.stringify(medidas, null, 2),
    contentType: 'application/json',
  })
  console.log(`[anchos] ${JSON.stringify(medidas)}`)
  return medidas
}

function comprobarSinDesborde(m: Medidas, tablasMinimas: number) {
  expect(m.tablas.length, `tablas en ${m.ruta} a ${m.viewport}`).toBeGreaterThanOrEqual(tablasMinimas)
  for (const t of m.tablas) {
    expect(
      t.tablaScrollWidth,
      `${m.ruta} ${m.viewport} «${t.caption}»: table.scrollWidth <= contenedor.clientWidth (columnas ${JSON.stringify(t.columnas)})`,
    ).toBeLessThanOrEqual(t.contenedorClientWidth)
  }
  expect(
    m.documentoScrollWidth,
    `${m.ruta} ${m.viewport}: sin desplazamiento horizontal de la pagina`,
  ).toBeLessThanOrEqual(m.innerWidth)
}

async function abrirLista(page: Page) {
  await page.goto('/lista')
  await expect(page.getByRole('heading', { level: 1, name: 'Lista priorizada' })).toBeVisible()
  await expect(page.getByRole('columnheader', { name: 'Gestión' }).first()).toBeVisible({
    timeout: 30_000,
  })
}

async function abrirSeguimiento(page: Page) {
  await page.goto('/seguimiento?filtro=proximas')
  await expect(page.getByRole('table', { name: 'Gestiones pendientes' })).toBeVisible({
    timeout: 30_000,
  })
  await expect(page.getByRole('cell', { name: RESPONSABLE, exact: true }).first()).toBeVisible()
}

async function abrirCampanias(page: Page) {
  await page.goto('/campanias')
  await expect(page.getByRole('cell', { name: NOMBRE_CAMPANIA, exact: true })).toBeVisible({
    timeout: 30_000,
  })
}

async function abrirDashboard(page: Page) {
  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { level: 1, name: 'Dashboard' })).toBeVisible()
  await expect(page.getByRole('cell', { name: NOMBRE_CAMPANIA, exact: true })).toBeVisible({
    timeout: 30_000,
  })
}

function carpetaCapturas(): string {
  return process.env.E2E_CAPTURAS_DIR ?? test.info().outputDir
}

test.describe.configure({ mode: 'serial' })

test.describe('anchos de las tablas (R-014)', () => {
  test.beforeEach(({ baseURL }) => {
    test.skip(
      !baseURL || baseURL.includes(PUERTO_PRINCIPAL),
      'Crea campaña, carga, lista y gestiones: solo contra el stack E2E aislado (E2E_BASE_URL=http://localhost:8081).',
    )
  })

  test('prepara datos realistas: campaña larga, carga, lista y dos gestiones', async ({ page }) => {
    test.setTimeout(180_000)

    await test.step('campaña con nombre y descripción largos (todos los niveles y planes)', async () => {
      await page.goto('/campanias')
      await page.getByRole('button', { name: 'Nueva campaña' }).click()
      const dialogo = page.getByRole('dialog', { name: 'Nueva campaña' })
      await dialogo.getByLabel('Nombre').fill(NOMBRE_CAMPANIA)
      await dialogo.getByLabel('Descripción').fill(DESCRIPCION_CAMPANIA)
      for (const n of NIVELES) await grupo(dialogo, 'Niveles de riesgo').getByLabel(n).check()
      for (const p of PLANES) await grupo(dialogo, 'Planes').getByLabel(p).check()
      await dialogo.getByLabel('Prioridad').fill('1')
      const creada = page.waitForResponse(
        (r) => r.request().method() === 'POST' && /\/api\/v1\/campanias$/.test(r.url()),
      )
      await dialogo.getByRole('button', { name: 'Guardar' }).click()
      expect((await creada).status()).toBe(201)
      await expect(dialogo).toHaveCount(0)
    })

    const cedulas = await test.step('carga de 10 socios con nombres largos', async () => {
      const ruta = test.info().outputPath('plantilla_anchos.xlsx')
      const generadas = await crearPlantillaLarga(ruta)
      await page.goto('/carga')
      await page.getByLabel('Archivo de la plantilla (.xlsx)').setInputFiles(ruta)
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
      return generadas
    })

    await test.step('generar la lista de hoy (valores por defecto)', async () => {
      await page.goto('/lista')
      const creada = page.waitForResponse(
        (r) => r.request().method() === 'POST' && /\/api\/v1\/listas$/.test(r.url()),
      )
      await page.getByRole('button', { name: 'Generar lista' }).click()
      expect((await creada).status()).toBe(201)
      await expect(
        page.getByRole('cell', { name: new RegExp(`^(${cedulas.join('|')})$`) }).first(),
      ).toBeVisible({ timeout: 30_000 })
    })

    const filasNuevas = page
      .getByRole('row')
      .filter({ has: page.getByRole('cell', { name: new RegExp(`^(${cedulas.join('|')})$`) }) })
      .filter({ has: page.getByRole('button', { name: /^Gestionar prioridad \d+$/ }) })

    async function abrirGestion(): Promise<string> {
      const boton = filasNuevas.first().getByRole('button', { name: /^Gestionar prioridad \d+$/ })
      const etiqueta = (await boton.getAttribute('aria-label')) ?? ''
      await boton.click()
      return etiqueta.replace('Gestionar prioridad ', '')
    }

    await test.step('gestión pendiente con la campaña larga y responsable largo (+3 días)', async () => {
      const prioridad = await abrirGestion()
      const dialogo = page.getByRole('dialog', { name: `Gestión de la prioridad ${prioridad}` })
      const nueva = dialogo.getByRole('form', { name: 'Nueva gestión' })
      await nueva.getByLabel(NOMBRE_CAMPANIA).check()
      await nueva.getByLabel('Fecha de seguimiento').fill(hoyMasLocal(3))
      await nueva.getByLabel('Responsable (opcional)').fill(RESPONSABLE)
      const creada = page.waitForResponse(
        (r) => r.request().method() === 'POST' && /\/api\/v1\/gestiones$/.test(r.url()),
      )
      await nueva.getByRole('button', { name: 'Crear gestión' }).click()
      expect((await creada).status()).toBe(201)
      await expect(dialogo).toHaveCount(0)
      await expect(
        page.getByRole('button', { name: `Registrar resultado prioridad ${prioridad}`, exact: true }),
      ).toBeVisible({ timeout: 30_000 })
    })

    await test.step('gestión cerrada sin campaña en otro socio', async () => {
      const prioridad = await abrirGestion()
      const dialogo = page.getByRole('dialog', { name: `Gestión de la prioridad ${prioridad}` })
      const nueva = dialogo.getByRole('form', { name: 'Nueva gestión' })
      await nueva.getByLabel('No asignar campaña').check()
      const creada = page.waitForResponse(
        (r) => r.request().method() === 'POST' && /\/api\/v1\/gestiones$/.test(r.url()),
      )
      await nueva.getByRole('button', { name: 'Crear gestión' }).click()
      expect((await creada).status()).toBe(201)
      await expect(dialogo).toHaveCount(0)
      await expect(
        page.getByRole('button', { name: `Ver gestión prioridad ${prioridad}`, exact: true }),
      ).toBeVisible({ timeout: 30_000 })
    })
  })

  for (const viewport of ESCRITORIO) {
    test(`a ${viewport.width}x${viewport.height} ninguna tabla desborda en Lista, Seguimiento, Campañas y Dashboard`, async ({
      page,
    }) => {
      test.setTimeout(120_000)
      await page.setViewportSize(viewport)

      await test.step('/lista: las dos tablas (prioritarios y otros) con Gestión/Campaña/Acción', async () => {
        await abrirLista(page)
        await expect(page.getByRole('table', { name: 'Socios prioritarios a contactar' })).toBeVisible()
        await expect(page.getByRole('table', { name: 'Otros socios por vencer' })).toBeVisible()
        await expect(page.getByRole('cell', { name: NOMBRE_CAMPANIA, exact: true })).toBeVisible()
        await expect(page.getByRole('cell', { name: 'Sin campaña', exact: true }).first()).toBeVisible()
        comprobarSinDesborde(await medir(page, '/lista'), 2)
        await page.screenshot({
          path: join(carpetaCapturas(), `lista-${viewport.width}.png`),
          fullPage: true,
        })
      })

      await test.step('/seguimiento?filtro=proximas', async () => {
        await abrirSeguimiento(page)
        comprobarSinDesborde(await medir(page, '/seguimiento?filtro=proximas'), 1)
      })

      await test.step('/campanias', async () => {
        await abrirCampanias(page)
        comprobarSinDesborde(await medir(page, '/campanias'), 1)
      })

      await test.step('/dashboard', async () => {
        await abrirDashboard(page)
        comprobarSinDesborde(await medir(page, '/dashboard'), 3)
      })
    })
  }

  test('a 390x844 la página de la lista no desborda y la tabla se desplaza dentro de su contenedor', async ({
    page,
  }) => {
    await page.setViewportSize(MOVIL)
    await abrirLista(page)

    const pagina = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      documentoScrollWidth: document.documentElement.scrollWidth,
    }))
    expect(pagina.documentoScrollWidth).toBeLessThanOrEqual(pagina.innerWidth)

    const tabla = page.getByRole('table', { name: 'Socios prioritarios a contactar' })
    const contenedor = tabla.locator('xpath=..')
    await expect(contenedor).toHaveCSS('overflow-x', 'auto')
    const anchos = await contenedor.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }))
    console.log(`[anchos] 390x844 /lista contenedor ${JSON.stringify(anchos)}`)
    expect(anchos.scrollWidth, 'a 390 px la tabla es mas ancha y se desplaza').toBeGreaterThan(
      anchos.clientWidth,
    )

    const accion = tabla
      .getByRole('row')
      .nth(1)
      .getByRole('button', { name: /prioridad \d+$/ })
    await contenedor.evaluate((el) => {
      el.scrollLeft = el.scrollWidth
    })
    // Lleva la fila a la vista en vertical sin tocar el desplazamiento horizontal de la tabla.
    await accion.evaluate((el) => {
      window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 200)
    })
    await expect(accion).toBeInViewport()
    // Desplazar la tabla no desplaza la pagina.
    expect(await page.evaluate(() => window.scrollX)).toBe(0)
  })

  test('al imprimir el Dashboard a 1366 px la cabecera se oculta y las tablas no se recortan', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1366, height: 768 })
    await abrirDashboard(page)
    await expect(page.getByRole('banner')).toBeVisible()
    expect(await page.getByRole('button').filter({ visible: true }).count()).toBeGreaterThan(0)
    await page.emulateMedia({ media: 'print' })

    // Cabecera de la aplicacion (landmark banner) y botones ocultos al imprimir.
    await expect(page.getByRole('banner')).toBeHidden()
    await expect(page.getByRole('button').filter({ visible: true })).toHaveCount(0)
    for (const nombre of ['Datos del embudo', 'Datos del gráfico de resultados', 'Resultados por campaña']) {
      await expect(page.getByRole('table', { name: nombre })).toBeAttached()
    }
    const m = await medir(page, '/dashboard (print)')
    expect(m.tablas.length).toBeGreaterThanOrEqual(3)
    for (const t of m.tablas) {
      expect(
        t.tablaScrollWidth,
        `print «${t.caption}»: sin recorte (columnas ${JSON.stringify(t.columnas)})`,
      ).toBeLessThanOrEqual(t.contenedorClientWidth)
    }
    for (const nombre of ['Datos del embudo', 'Datos del gráfico de resultados', 'Resultados por campaña']) {
      const overflow = await page
        .getByRole('table', { name: nombre })
        .locator('xpath=..')
        .evaluate((el) => getComputedStyle(el).overflowX)
      expect(overflow, `print «${nombre}»: contenedor sin recorte`).toBe('visible')
    }
  })
})
