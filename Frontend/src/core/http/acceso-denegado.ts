/**
 * Estado minimo "acceso denegado" (CU-00): el cliente HTTP lo marca al recibir un `403 forbidden`
 * y el layout lo lee con `useSyncExternalStore`. Una vez marcado se queda asi hasta recargar la
 * pagina: el equipo no cambia de autorizacion sin reiniciar el servidor.
 */

type Oyente = () => void

let denegado = false
const oyentes = new Set<Oyente>()

/** Marca el acceso como denegado; los suscriptores se notifican solo la primera vez. */
export function marcarAccesoDenegado(): void {
  if (denegado) return
  denegado = true
  for (const oyente of [...oyentes]) oyente()
}

export function estaDenegado(): boolean {
  return denegado
}

/** Suscribe un oyente; devuelve la funcion que lo da de baja. */
export function suscribir(oyente: Oyente): () => void {
  oyentes.add(oyente)
  return () => {
    oyentes.delete(oyente)
  }
}

/** Solo para pruebas: vuelve al estado inicial (el estado vive en el modulo). */
export function reiniciarAccesoDenegado(): void {
  denegado = false
}
