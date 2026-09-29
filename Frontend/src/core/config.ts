/**
 * Configuracion publica de la aplicacion.
 * Las variables VITE_* se exponen en el bundle: nunca contienen secretos.
 */
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
  /** Activa los mocks de red (MSW) en desarrollo. Sin efecto en el build de produccion. */
  apiMocks: import.meta.env.VITE_API_MOCKS === 'true',
} as const
