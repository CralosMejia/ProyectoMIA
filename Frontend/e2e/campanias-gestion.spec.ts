import ExcelJS from 'exceljs'
import { expect, type Locator, type Page, test } from '@playwright/test'
import { crearPlantillaSintetica } from './plantilla-sintetica'

/**
 * Recorrido critico del Dia 5 (R-009): campaña -> lista -> gestion -> resultado -> Excel.
 *
 * CREA una campaña, una carga, una lista y una gestion: se ejecuta SOLO contra el stack aislado
 * `mtabolic-e2e` (E2E_BASE_URL=http://localhost:8081), nunca contra el principal.
 * Solo datos ficticios (plantilla sintetica); la fila se identifica por su prioridad.
 */

const PUERTO_PRINCIPAL = ':8080'
const CAMPANIAS_EJEMPLO = 3
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

test('crea una campaña, gestiona un socio de la lista y cierra la gestion', async ({
  page,
  baseURL,
}) => {
  test.skip(
    !baseURL || baseURL.includes(PUERTO_PRINCIPAL),
    'Crea campaña, carga, lista y gestion: solo contra el stack E2E aislado (E2E_BASE_URL=http://localhost:8081).',
  )
  test.setTimeout(180_000)

  const nombreCampania = `Campaña E2E ${Date.now()}`

  await test.step('Campañas muestra las 3 de ejemplo', async () => {
    await page.goto('/campanias')
    await expect(page.getByRole('heading', { level: 1, name: 'Campañas' })).toBeVisible()
    await expect(page.getByRole('table').getByText('Ejemplo', { exact: true })).toHaveCount(
      CAMPANIAS_EJEMPLO,
    )
  })

  await test.step('crear la campaña (Alto/Medio, todos los planes, prioridad 1)', async () => {
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
    await expect(page.getByRole('cell', { name: nombreCampania, exact: true })).toBeVisible()
  })

  await test.step('cargar socios ficticios y generar la lista', async () => {
    const plantilla = await crearPlantillaSintetica(test.info().outputPath('plantilla_e2e.xlsx'))
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
    await expect(page.getByRole('columnheader', { name: 'Campaña' }).first()).toBeVisible()
  })

  const prioridad = await test.step('abrir «Gestionar» en un socio de riesgo alto o medio', async () => {
    const fila = page
      .getByRole('row')
      .filter({ has: page.getByRole('button', { name: /^Gestionar prioridad \d+$/ }) })
      .filter({ has: page.getByText(/^(Alto|Medio)$/) })
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

  await test.step('crear la gestion con la campaña creada y la fecha sugerida', async () => {
    const nueva = dialogo.getByRole('form', { name: 'Nueva gestión' })
    await expect(nueva).toBeVisible()
    await nueva.getByLabel(nombreCampania).check()
    await expect(nueva.getByLabel('Fecha de seguimiento')).not.toHaveValue('')
    await nueva.getByRole('button', { name: 'Crear gestión' }).click()
    await expect(dialogo.getByRole('form', { name: 'Resultado del seguimiento' })).toBeVisible()
  })

  await test.step('registrar el resultado: contactado, ofrecida y aceptada Sí; renovó No', async () => {
    const resultado = dialogo.getByRole('form', { name: 'Resultado del seguimiento' })
    await expect(resultado.getByText(nombreCampania)).toBeVisible()
    await grupo(resultado, '¿Se contactó al socio?').getByLabel('Sí', { exact: true }).check()
    await grupo(resultado, '¿Se ofreció la campaña?').getByLabel('Sí', { exact: true }).check()
    await grupo(resultado, '¿Aceptó la campaña?').getByLabel('Sí', { exact: true }).check()
    await resultado.getByLabel('Fecha del contacto').fill(hoyLocal())
    await grupo(resultado, '¿Renovó?').getByLabel('No', { exact: true }).check()
    await resultado.getByRole('button', { name: 'Guardar resultado' }).click()
    await expect(dialogo.getByText('Gestión cerrada: no se puede modificar.')).toBeVisible()
    await dialogo.getByRole('button', { name: 'Cerrar' }).click()
    await expect(dialogo).toHaveCount(0)
  })

  await test.step('la fila muestra «Cerrada» y «Ver gestión» es de solo lectura', async () => {
    await expect(fila.getByRole('cell', { name: 'Cerrada', exact: true })).toBeVisible()
    await expect(fila.getByRole('cell', { name: nombreCampania, exact: true })).toBeVisible()
    await fila.getByRole('button', { name: `Ver gestión prioridad ${prioridad}` }).click()
    await expect(dialogo.getByText('Gestión cerrada: no se puede modificar.')).toBeVisible()
    await expect(dialogo.getByRole('button', { name: 'Guardar resultado' })).toHaveCount(0)
    await dialogo.getByRole('button', { name: 'Cerrar' }).click()
  })

  await test.step('el Excel lleva «Cerrada» en la columna «Gestión» y la campaña', async () => {
    const descarga = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Descargar Excel' }).click()
    const ruta = await (await descarga).path()

    const libro = new ExcelJS.Workbook()
    await libro.xlsx.readFile(ruta)
    const hoja = libro.worksheets[0]
    expect(hoja).toBeDefined()
    if (!hoja) return

    let filaTitulos = 0
    let colGestion = 0
    let colCampania = 0
    hoja.eachRow((row, numero) => {
      if (filaTitulos > 0) return
      row.eachCell((celda, columna) => {
        if (celda.text === 'Gestión') colGestion = columna
        if (celda.text === 'Campaña') colCampania = columna
      })
      if (colGestion > 0 && colCampania > 0) filaTitulos = numero
    })
    expect(filaTitulos).toBeGreaterThan(0)

    const cerradas: string[] = []
    hoja.eachRow((row, numero) => {
      if (numero > filaTitulos && row.getCell(colGestion).text === 'Cerrada') {
        cerradas.push(row.getCell(colCampania).text)
      }
    })
    expect(cerradas).toContain(nombreCampania)
  })
})
