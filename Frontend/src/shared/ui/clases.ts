/**
 * Clases de la guia de estilo compartidas (R-013, T21). Solo tokens de `src/index.css`.
 * Viven fuera de `Diseno.tsx` para que ese modulo solo exporte componentes (react-refresh).
 *
 * - `CLASE_CAMPO`: campo de texto, `<select>` o `<textarea>`: superficie blanca, borde `line`,
 *   foco `brand`, borde `danger` con `aria-invalid="true"`, deshabilitado sobre `canvas` al 50 %.
 *   Para colocar, anade clases despues (`${CLASE_CAMPO} max-w-md`).
 * - `claseBoton(variante)`: clases de `Boton` para elementos que no son `<button>` (p. ej. un
 *   `Link` con aspecto de boton). Mismas variantes y foco que `Boton`.
 */

export type VarianteBoton = 'primario' | 'secundario' | 'peligro'

export const CLASE_CAMPO =
  'rounded-card border border-line bg-surface px-3 py-2 text-sm text-ink shadow-sm focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-brand disabled:cursor-not-allowed disabled:bg-canvas disabled:opacity-50 aria-[invalid=true]:border-danger'

const BASE_BOTON =
  'inline-flex items-center justify-center gap-2 rounded-pill border px-4 py-2 font-sans text-sm font-medium shadow-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-50'

const VARIANTE_BOTON: Record<VarianteBoton, string> = {
  primario:
    'border-brand bg-brand text-surface hover:border-brand-strong hover:bg-brand-strong focus-visible:outline-brand disabled:hover:bg-brand',
  secundario:
    'border-line bg-surface text-ink hover:bg-canvas focus-visible:outline-brand disabled:hover:bg-surface',
  peligro:
    'border-danger bg-danger text-surface hover:bg-danger/90 focus-visible:outline-danger disabled:hover:bg-danger',
}

/** Clases de boton de la guia para la `variante` dada (por defecto `'secundario'`). */
export function claseBoton(variante: VarianteBoton = 'secundario'): string {
  return `${BASE_BOTON} ${VARIANTE_BOTON[variante]}`
}
