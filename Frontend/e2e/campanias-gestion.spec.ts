import ExcelJS from 'exceljs'
import { expect, type Locator, type Page, test } from '@playwright/test'
import { crearPlantillaSintetica } from './plantilla-sintetica'

/**
 * Recorrido critico del Dia 5 (R-009): campaña -> lista -> gestion -> resultado -> Excel.
 * R-010 añade: inactivar y volver a activar la campaña (y que se siga sugiriendo), la ayuda de la
 * lista con las secciones de campañas y gestion, y la gestion con «No asignar campaña», que nace
 * cerrada (sin fecha de seguimiento ni responsable, y sin resultado que registrar).
 * R-012: crear con campaña cierra la ventana; el resultado se anota luego con «Registrar resultado
 * prioridad N» de la fila, y al guardarlo la ventana tambien se cierra.
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

test('crea y reactiva una campaña, gestiona socios con y sin campaña y cierra la gestion', async ({
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

  await test.step('inactivar la campaña y volver a activarla con «Activar <nombre>»', async () => {
    const filaCampania = page
      .getByRole('row')
      .filter({ has: page.getByRole('cell', { name: nombreCampania, exact: true }) })
    const activar = filaCampania.getByRole('button', {
      name: `Activar ${nombreCampania}`,
      exact: true,
    })
    const inactivar = filaCampania.getByRole('button', {
      name: `Inactivar ${nombreCampania}`,
      exact: true,
    })
    await expect(filaCampania.getByRole('cell', { name: 'Activa', exact: true })).toBeVisible()
    await expect(activar).toHaveCount(0)

    await inactivar.click()
    const confirmacion = page.getByRole('dialog', { name: 'Inactivar campaña' })
    const inactivada = page.waitForResponse(
      (r) =>
        r.request().method() === 'POST' && /\/api\/v1\/campanias\/\d+\/inactivar$/.test(r.url()),
    )
    await confirmacion.getByRole('button', { name: 'Inactivar', exact: true }).click()
    expect((await inactivada).status()).toBe(200)
    await expect(confirmacion).toHaveCount(0)
    await expect(filaCampania.getByRole('cell', { name: 'Inactiva', exact: true })).toBeVisible()
    await expect(activar).toBeVisible()
    await expect(inactivar).toHaveCount(0)

    const activada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/campanias\/\d+\/activar$/.test(r.url()),
    )
    await activar.click()
    expect((await activada).status()).toBe(200)
    // Sin ventana de confirmacion: la fila cambia en su sitio.
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(filaCampania.getByRole('cell', { name: 'Activa', exact: true })).toBeVisible()
    await expect(inactivar).toBeVisible()
    await expect(activar).toHaveCount(0)
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

  await test.step('la ayuda muestra las secciones «Campañas» y «Gestionar a un socio»', async () => {
    const botonAyuda = page.getByRole('button', { name: '¿Cómo funciona esta lista?' })
    await botonAyuda.click()
    const ayuda = page.getByRole('dialog', { name: '¿Cómo funciona esta lista?' })
    await expect(ayuda.getByRole('heading', { name: 'Campañas', exact: true })).toBeVisible()
    await expect(
      ayuda.getByRole('heading', { name: 'Gestionar a un socio', exact: true }),
    ).toBeVisible()
    await ayuda.getByRole('button', { name: 'Cerrar' }).click()
    await expect(ayuda).toHaveCount(0)
    await expect(botonAyuda).toBeFocused()
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

  await test.step('la campaña reactivada vuelve a sugerirse: crear la gestion con ella y la fecha sugerida', async () => {
    const nueva = dialogo.getByRole('form', { name: 'Nueva gestión' })
    await expect(nueva).toBeVisible()
    await expect(nueva.getByLabel(nombreCampania)).toBeVisible()
    await nueva.getByLabel(nombreCampania).check()
    await expect(nueva.getByLabel('Fecha de seguimiento')).not.toHaveValue('')
    const creada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/gestiones$/.test(r.url()),
    )
    await nueva.getByRole('button', { name: 'Crear gestión' }).click()
    expect((await creada).status()).toBe(201)
    // R-012 (e): con exito la ventana se cierra y la lista se recarga; ya no pasa a la parte 2.
    await expect(dialogo).toHaveCount(0)
    await expect(page.getByRole('form', { name: 'Resultado del seguimiento' })).toHaveCount(0)
  })

  await test.step('la fila queda «Pendiente», con la campaña y «Registrar resultado»', async () => {
    await expect(fila.getByRole('cell', { name: 'Pendiente', exact: true })).toBeVisible({
      timeout: 30_000,
    })
    await expect(fila.getByRole('cell', { name: nombreCampania, exact: true })).toBeVisible()
    await expect(
      fila.getByRole('button', { name: `Registrar resultado prioridad ${prioridad}`, exact: true }),
    ).toBeVisible()
  })

  await test.step('registrar el resultado desde la fila: contactado, ofrecida y aceptada Sí; renovó No', async () => {
    await fila
      .getByRole('button', { name: `Registrar resultado prioridad ${prioridad}`, exact: true })
      .click()
    const resultado = dialogo.getByRole('form', { name: 'Resultado del seguimiento' })
    await expect(resultado).toBeVisible()
    await expect(resultado.getByText(nombreCampania)).toBeVisible()
    await grupo(resultado, '¿Se contactó al socio?').getByLabel('Sí', { exact: true }).check()
    await grupo(resultado, '¿Se ofreció la campaña?').getByLabel('Sí', { exact: true }).check()
    await grupo(resultado, '¿Aceptó la campaña?').getByLabel('Sí', { exact: true }).check()
    await resultado.getByLabel('Fecha del contacto').fill(hoyLocal())
    await grupo(resultado, '¿Renovó?').getByLabel('No', { exact: true }).check()
    const registrado = page.waitForResponse(
      (r) => r.request().method() === 'PUT' && /\/api\/v1\/gestiones\/\d+\/resultado$/.test(r.url()),
    )
    await resultado.getByRole('button', { name: 'Guardar resultado' }).click()
    expect((await registrado).status()).toBe(200)
    // R-012 (e): al guardar con exito la ventana se cierra sola.
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

  const prioridadSin = await test.step('abrir «Gestionar» en otro socio sin gestion', async () => {
    const boton = page.getByRole('button', { name: /^Gestionar prioridad \d+$/ }).first()
    await expect(boton).toBeVisible()
    const etiqueta = (await boton.getAttribute('aria-label')) ?? ''
    await boton.click()
    return etiqueta.replace('Gestionar prioridad ', '')
  })
  expect(prioridadSin).not.toBe(prioridad)

  const dialogoSin = page.getByRole('dialog', { name: `Gestión de la prioridad ${prioridadSin}` })
  const accionesSin = page.getByRole('button', { name: new RegExp(`prioridad ${prioridadSin}$`) })
  const filaSin = page.getByRole('row').filter({ has: accionesSin })
  const verGestionSin = page.getByRole('button', {
    name: `Ver gestión prioridad ${prioridadSin}`,
    exact: true,
  })

  await test.step('«No asignar campaña»: sin fecha ni responsable, y la ventana se cierra al guardar', async () => {
    const nueva = dialogoSin.getByRole('form', { name: 'Nueva gestión' })
    await expect(nueva).toBeVisible()
    await nueva.getByLabel('No asignar campaña').check()
    await expect(nueva.getByLabel('Fecha de seguimiento')).toHaveCount(0)
    await expect(nueva.getByLabel('Responsable (opcional)')).toHaveCount(0)
    await expect(
      nueva.getByText('Sin campaña, la gestión queda cerrada y no tendrá seguimiento.'),
    ).toBeVisible()

    const creada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/gestiones$/.test(r.url()),
    )
    await nueva.getByRole('button', { name: 'Crear gestión' }).click()
    const respuesta = await creada
    expect(respuesta.status()).toBe(201)
    expect(respuesta.request().postDataJSON()).toMatchObject({
      campania_id: null,
      fecha_seguimiento: null,
      responsable: null,
    })
    // No pasa a «Resultado del seguimiento»: la ventana se cierra sola.
    await expect(dialogoSin).toHaveCount(0)
    await expect(page.getByRole('form', { name: 'Resultado del seguimiento' })).toHaveCount(0)
  })

  await test.step('la fila queda «Cerrada», «Sin campaña» y con «Ver gestión» como unica accion', async () => {
    await expect(filaSin.getByRole('cell', { name: 'Cerrada', exact: true })).toBeVisible()
    await expect(filaSin.getByRole('cell', { name: 'Sin campaña', exact: true })).toBeVisible()
    await expect(verGestionSin).toBeVisible()
    await expect(accionesSin).toHaveCount(1)
  })

  await test.step('«Ver gestión» solo muestra «No se le asignó campaña»', async () => {
    await verGestionSin.click()
    await expect(dialogoSin.getByText('No se le asignó campaña', { exact: true })).toBeVisible()
    await expect(page.getByRole('form', { name: 'Resultado del seguimiento' })).toHaveCount(0)
    await expect(page.getByRole('form', { name: 'Nueva gestión' })).toHaveCount(0)
    await expect(dialogoSin.getByRole('button', { name: 'Guardar resultado' })).toHaveCount(0)
    await expect(dialogoSin.getByRole('radio')).toHaveCount(0)
    await expect(dialogoSin.getByRole('textbox')).toHaveCount(0)
    await expect(dialogoSin.getByText('Fecha de seguimiento')).toHaveCount(0)
    // Lo unico que se puede hacer es cerrar.
    await expect(dialogoSin.getByRole('button')).toHaveCount(1)
    await dialogoSin.getByRole('button', { name: 'Cerrar' }).click()
    await expect(dialogoSin).toHaveCount(0)
    await expect(verGestionSin).toBeFocused()
  })

  await test.step('el Excel lleva «Cerrada» en «Gestión», la campaña y «Sin campaña»', async () => {
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
    expect(cerradas).toContain('Sin campaña')
  })
})
