import { expect, test } from '@playwright/test'

test('la pantalla de inicio muestra el estado del sistema y de la base de datos', async ({
  page,
}) => {
  await page.goto('/salud')

  await expect(page.getByText('Sistema operativo')).toBeVisible()
  await expect(page.getByText('Base de datos: conectada')).toBeVisible()
})
