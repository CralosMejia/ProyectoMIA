import { expect, test } from '@playwright/test'

/**
 * R-021 (T2, definicion (f)): la tarjeta "¿Cómo le fue a la lista del mes?" a ancho de telefono y
 * con el modo oscuro forzado de Chromium (auto dark mode, via CDP).
 *
 * Solo lectura: abre el Dashboard del mes en curso; no crea datos. Se ejecuta contra el stack E2E
 * aislado (E2E_BASE_URL=http://localhost:8081), como el resto de specs del piloto.
 */

const PUERTO_PRINCIPAL = ':8080'
const TITULO_PILOTO = '¿Cómo le fue a la lista del mes?'
const GRAFICOS = [
  '¿Cuántos contactamos y cuántos renovaron?',
  '¿Con cuánta anticipación?',
] as const

test.describe('indicadores del piloto (R-021): teléfono y modo oscuro forzado', () => {
  test.beforeEach(({ baseURL }) => {
    test.skip(
      !baseURL || baseURL.includes(PUERTO_PRINCIPAL),
      'Solo contra el stack E2E aislado (E2E_BASE_URL=http://localhost:8081).',
    )
  })

  test('a 390x844 los dos gráficos se apilan en una columna y nada desborda', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/dashboard')
    const seccion = page.getByRole('region', { name: TITULO_PILOTO })
    await expect(seccion).toBeVisible({ timeout: 30_000 })

    const medidas = await page.evaluate(() => ({
      documento: document.documentElement.scrollWidth,
      ventana: window.innerWidth,
    }))
    expect(medidas.documento).toBeLessThanOrEqual(medidas.ventana)

    const tarjeta = await seccion.evaluate((el) => ({
      scroll: el.scrollWidth,
      client: el.clientWidth,
    }))
    expect(tarjeta.scroll).toBeLessThanOrEqual(tarjeta.client)

    const cajas = []
    for (const titulo of GRAFICOS) {
      const grafico = seccion.getByRole('region', { name: titulo })
      await expect(grafico).toBeVisible()
      const caja = await grafico.boundingBox()
      expect(caja).not.toBeNull()
      cajas.push(caja!)
      // Cada grafico cabe en la ventana del telefono.
      expect(caja!.x).toBeGreaterThanOrEqual(0)
      expect(caja!.x + caja!.width).toBeLessThanOrEqual(390 + 0.5)
      const interno = await grafico.evaluate((el) => el.scrollWidth <= el.clientWidth)
      expect(interno).toBe(true)
    }
    // R-022: las etiquetas de la escala y del promedio caben dentro del grafico.
    const anticipacion = seccion.getByRole('region', { name: '¿Con cuánta anticipación?' })
    const limites = await anticipacion.boundingBox()
    expect(limites).not.toBeNull()
    for (const etiqueta of await anticipacion.locator('[data-marca] > span:last-child').all()) {
      const caja = await etiqueta.boundingBox()
      expect(caja).not.toBeNull()
      expect(caja!.x).toBeGreaterThanOrEqual(limites!.x - 0.5)
      expect(caja!.x + caja!.width).toBeLessThanOrEqual(limites!.x + limites!.width + 0.5)
    }

    // Una columna: cada grafico empieza debajo del anterior.
    for (let i = 1; i < cajas.length; i++) {
      expect(cajas[i].y).toBeGreaterThanOrEqual(cajas[i - 1].y + cajas[i - 1].height - 0.5)
    }
  })

  test('con el modo oscuro forzado de Chromium la tarjeta sigue visible y legible', async ({
    page,
    browserName,
  }, testInfo) => {
    test.skip(browserName !== 'chromium', 'Auto dark mode solo existe en Chromium (CDP).')
    const cdp = await page.context().newCDPSession(page)
    await cdp.send('Emulation.setAutoDarkModeOverride', { enabled: true })
    await page.emulateMedia({ colorScheme: 'dark' })

    await page.setViewportSize({ width: 1366, height: 900 })
    await page.goto('/dashboard')
    const seccion = page.getByRole('region', { name: TITULO_PILOTO })
    await expect(seccion).toBeVisible({ timeout: 30_000 })
    for (const titulo of GRAFICOS) {
      await expect(seccion.getByRole('region', { name: titulo }).getByRole('img')).toBeVisible()
    }

    // R-022: la linea base de "¿Con cuánta anticipación?" es solida (sin opacidad que el oscuro
    // automatico aplane), de al menos 2 px, y la marca "Vence" se ve.
    const anticipacion = seccion.getByRole('region', { name: '¿Con cuánta anticipación?' })
    const linea = await anticipacion.locator('[data-linea-anticipacion]').evaluate((el) => ({
      opacidad: getComputedStyle(el).opacity,
      color: getComputedStyle(el).borderTopColor,
      alto: Number.parseFloat(getComputedStyle(el).borderTopWidth),
    }))
    expect(linea.opacidad).toBe('1')
    expect(linea.alto).toBeGreaterThanOrEqual(2)
    expect(linea.color).not.toMatch(/(rgba\(.*,\s*0(\.\d+)?\)|\/\s*0?\.\d+\))$/)
    const vence = anticipacion.locator('[data-marca="Vencimiento"]')
    await expect(vence).toBeVisible()
    await expect(vence.getByText('Vence', { exact: true })).toBeVisible()
    const capturaAnticipacion = await anticipacion.screenshot(
      process.env.ANTICIPACION_CAPTURA ? { path: process.env.ANTICIPACION_CAPTURA } : {},
    )
    await testInfo.attach('anticipacion-oscuro.png', {
      body: capturaAnticipacion,
      contentType: 'image/png',
    })

    // El fondo efectivamente se oscurece (prueba de que el modo forzado se aplico) y la tarjeta
    // no queda en blanco: se compara la luminancia media de la captura con la de un fondo plano.
    const captura = await seccion.screenshot(
      process.env.PILOTO_CAPTURA ? { path: process.env.PILOTO_CAPTURA } : {},
    )
    await testInfo.attach('piloto-oscuro.png', { body: captura, contentType: 'image/png' })
    const { media, desviacion } = await page.evaluate(async (b64) => {
      const img = new Image()
      img.src = `data:image/png;base64,${b64}`
      await img.decode()
      const c = document.createElement('canvas')
      c.width = img.width
      c.height = img.height
      const ctx = c.getContext('2d')!
      ctx.drawImage(img, 0, 0)
      const d = ctx.getImageData(0, 0, c.width, c.height).data
      let suma = 0
      let suma2 = 0
      const n = d.length / 4
      for (let i = 0; i < d.length; i += 4) {
        const l = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2]
        suma += l
        suma2 += l * l
      }
      const m = suma / n
      return { media: m, desviacion: Math.sqrt(suma2 / n - m * m) }
    }, captura.toString('base64'))
    // Fondo oscuro (el modo forzado oscurece la tarjeta blanca)...
    expect(media).toBeLessThan(128)
    // ...y con contenido distinguible del fondo (texto, barras, puntitos).
    expect(desviacion).toBeGreaterThan(20)
  })
})
