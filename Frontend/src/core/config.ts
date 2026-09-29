/**
 * Configuracion publica de la aplicacion.
 * Las variables VITE_* se exponen en el bundle: nunca contienen secretos.
 */
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
} as const
