import { stat } from 'node:fs/promises'
import { expect, type Locator, type Page, test } from '@playwright/test'
import { crearPlantillaSintetica } from './plantilla-sintetica'

/**
 * Recorrido critico D4-OP-01: carga valida -> generar lista -> descargar Excel.
 *
 * CONFIRMA una carga: se ejecuta SOLO contra el stack aislado `mtabolic-e2e`
 * (E2E_BASE_URL=http://localhost:8081), nunca contra el principal (decision (l) de R-007).
 */

const PUERTO_PRINCIPAL = ':8080'

/** Valor `<dd>` que sigue al termino `<dt>` dentro de `seccion`. */
function dato(seccion: Locator, termino: string): Locator {
  return seccion
    .locator('dt', { hasText: new RegExp(`^${termino}$`) })
    .locator('xpath=following-sibling::dd[1]')
}

async function irA(page: Page, enlace: string | RegExp, ruta: string) {
  const link = page.getByRole('link', { name: enlace }).first()
  if (await link.isVisible()) await link.click()
  else await page.goto(ruta)
}

test('carga una plantilla valida, genera la lista y descarga el Excel', async ({
  page,
  baseURL,
}) => {
  test.skip(
    !baseURL || baseURL.includes(PUERTO_PRINCIPAL),
    'Confirma una carga: solo contra el stack E2E aislado (E2E_BASE_URL=http://localhost:8081).',
  )
  test.setTimeout(120_000)

  const plantilla = await test.step('generar la plantilla sintetica', () =>
    crearPlantillaSintetica(test.info().outputPath('plantilla_e2e.xlsx')),
  )

  await test.step('subir la plantilla y ver la vista previa', async () => {
    await page.goto('/carga')
    await expect(page.getByRole('heading', { level: 1, name: 'Carga de datos' })).toBeVisible()
    await page.getByLabel('Archivo de la plantilla (.xlsx)').setInputFiles(plantilla.ruta)

    const vistaPrevia = page.getByRole('region', { name: 'Vista previa' })
    await expect(vistaPrevia).toBeVisible({ timeout: 30_000 })
    await expect(dato(vistaPrevia, 'Filas válidas')).toHaveText('3')
    await expect(dato(vistaPrevia, 'Filas con error')).toHaveText('0')
  })

  await test.step('confirmar y ver el resumen', async () => {
    await page.getByRole('button', { name: 'Confirmar' }).click()
    const resumen = page.getByRole('region', { name: 'Carga guardada' })
    await expect(resumen).toBeVisible({ timeout: 30_000 })
    await expect(dato(resumen, 'Filas guardadas')).toHaveText('3')
  })

  await test.step('generar la lista con los valores por defecto', async () => {
    await irA(page, 'Ver la lista de socios por vencer', '/lista')
    await expect(page.getByRole('heading', { level: 1, name: 'Lista priorizada' })).toBeVisible()

    const creada = page.waitForResponse(
      (r) => r.request().method() === 'POST' && /\/api\/v1\/listas$/.test(r.url()),
    )
    await page.getByRole('button', { name: 'Generar lista' }).click()
    expect((await creada).status()).toBe(201)

    await expect(page.getByText('Los datos pueden estar desactualizados')).toHaveCount(0)
    const cedulas = plantilla.socios.map((s) => s.cedula)
    const celda = page.getByRole('cell', { name: new RegExp(`^(${cedulas.join('|')})$`) })
    await expect(celda.first()).toBeVisible({ timeout: 30_000 })
    await expect(page.getByRole('cell', { name: /^SOCIO PRUEBA E2E/ }).first()).toBeVisible()
  })

  await test.step('descargar el Excel', async () => {
    const respuesta = page.waitForResponse((r) => /\/api\/v1\/listas\/\d+\/excel$/.test(r.url()))
    const descarga = page.waitForEvent('download')
    await page.getByRole('button', { name: 'Descargar Excel' }).click()

    const excel = await respuesta
    expect(excel.status()).toBe(200)
    expect(excel.headers()['content-type']).toContain('spreadsheetml')

    const archivo = await descarga
    expect(archivo.suggestedFilename()).toMatch(/\.xlsx$/)
    const ruta = await archivo.path()
    expect((await stat(ruta)).size).toBeGreaterThan(0)
  })
})
