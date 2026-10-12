import type { ComponentPropsWithRef, ReactNode } from 'react'
import { claseBoton, type VarianteBoton } from './clases'

/**
 * Primitivas de diseno compartidas (R-013, D7-FE-01). API estable para el rediseno por area.
 * Solo usan tokens de `src/index.css` (`@theme`); ningun color literal ni `style`.
 *
 * ## API
 *
 * - `Boton({ variante?, className?, ...props de <button> })`
 *   - `variante`: `'primario'` (accion principal, una por vista), `'secundario'` (por defecto) o
 *     `'peligro'` (acciones destructivas).
 *   - `type` es `"button"` por defecto; `type="submit"` se respeta. `disabled`, `onClick`,
 *     `aria-*` y `ref` pasan tal cual al `<button>`.
 *   - `className` se ANADE a las clases base (solo para colocacion: `self-start`, `w-full`...).
 * - `Tarjeta({ titulo?, nivelTitulo?, children, className?, ...props de <section> })`
 *   - `<section>` con fondo `surface`, borde `line`, radio `card`, sombra suave y `p-5`.
 *   - `titulo` opcional → encabezado `h2` (o `nivelTitulo` 2 | 3 | 4). La tarjeta NO se
 *     autoetiqueta: para que sea una region con nombre, pasa `aria-labelledby`/`aria-label`.
 * - `EncabezadoPagina({ titulo, subtitulo?, acciones? })`
 *   - Bloque (`<div>`, no crea landmark) con el unico `h1` de la pagina, subtitulo en `muted` y
 *     acciones alineadas a la derecha (se apilan debajo en pantallas estrechas).
 *
 * ## Guia de estilo (aplicar igual en todas las areas)
 *
 * - Color: fondo de pagina `bg-canvas`; contenedores `bg-surface`; texto `text-ink`; texto
 *   secundario `text-muted`; bordes `border-line`; marca/foco `brand` (hover `brand-strong`);
 *   destructivo `danger`; estados `ok`/`degraded`; riesgo `risk-high|medium|low`. Tintes de
 *   fondo con opacidad del token (`bg-brand/10`, `bg-degraded/10`), nunca paleta de Tailwind.
 * - Tipografia (`font-sans`): h1 `text-2xl font-semibold tracking-tight`; h2 de tarjeta
 *   `text-lg font-semibold`; h3 `text-base font-semibold`; cuerpo `text-sm`/`text-base`;
 *   metadatos y ayudas `text-sm text-muted`; cifras destacadas `text-3xl font-semibold tabular-nums`.
 * - Espaciado (escala de 4 px de Tailwind): entre bloques de pagina `gap-6`; dentro de una
 *   tarjeta `gap-4` y `p-5`; entre controles `gap-2`/`gap-3`; formularios `gap-4` por campo.
 * - Radios: tarjetas, ventanas y tablas `rounded-card`; botones, insignias y filtros `rounded-pill`.
 * - Botones: un solo `primario` por vista; el resto `secundario`; `peligro` solo si destruye o
 *   descarta. Foco visible siempre (`focus-visible:outline-*`); deshabilitado al 50 % de opacidad.
 * - Estados: carga `LoadingIndicator`; error `ErrorAlert`; vacio = texto `text-sm text-muted`
 *   dentro de la tarjeta; exito con `ok` (texto sobre `bg-ok/10`).
 */

export type { VarianteBoton }

export interface BotonProps extends ComponentPropsWithRef<'button'> {
  /** Jerarquia visual. Por defecto `'secundario'`. */
  variante?: VarianteBoton
}

/** Boton con las variantes de la guia. `type="button"` salvo que se indique otro. */
export function Boton({
  variante = 'secundario',
  type = 'button',
  className,
  ...props
}: BotonProps) {
  const clases = `${claseBoton(variante)}${className ? ` ${className}` : ''}`
  return <button type={type} className={clases} {...props} />
}

export interface TarjetaProps extends Omit<ComponentPropsWithRef<'section'>, 'title'> {
  /** Titulo visible de la tarjeta (encabezado). Sin titulo no hay encabezado. */
  titulo?: ReactNode
  /** Nivel del encabezado del titulo. Por defecto 2. */
  nivelTitulo?: 2 | 3 | 4
  children?: ReactNode
}

const ENCABEZADO = { 2: 'h2', 3: 'h3', 4: 'h4' } as const

/** Contenedor de seccion: superficie blanca con borde, radio y sombra suaves. */
export function Tarjeta({ titulo, nivelTitulo = 2, className, children, ...props }: TarjetaProps) {
  const Encabezado = ENCABEZADO[nivelTitulo]
  const clases = `flex flex-col gap-4 rounded-card border border-line bg-surface p-5 font-sans text-ink shadow-sm${className ? ` ${className}` : ''}`
  return (
    <section className={clases} {...props}>
      {titulo !== undefined && (
        <Encabezado className="text-lg font-semibold text-ink">{titulo}</Encabezado>
      )}
      {children}
    </section>
  )
}

export interface EncabezadoPaginaProps {
  /** Texto del unico `h1` de la pagina. */
  titulo: ReactNode
  /** Linea descriptiva bajo el titulo, en `muted`. */
  subtitulo?: ReactNode
  /** Botones u otros controles de la pagina (normalmente `Boton`). */
  acciones?: ReactNode
}

/** Encabezado de pagina: `h1`, subtitulo y acciones. */
export function EncabezadoPagina({ titulo, subtitulo, acciones }: EncabezadoPaginaProps) {
  return (
    <div className="flex flex-col gap-3 font-sans sm:flex-row sm:items-end sm:justify-between">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{titulo}</h1>
        {subtitulo !== undefined && <p className="text-sm text-muted">{subtitulo}</p>}
      </div>
      {acciones !== undefined && (
        <div className="flex flex-wrap items-center gap-2">{acciones}</div>
      )}
    </div>
  )
}
