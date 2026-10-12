import { Suspense, useSyncExternalStore } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { LoadingIndicator } from '../../shared/ui/LoadingIndicator'
import { estaDenegado, suscribir } from '../http/acceso-denegado'
import { AccesoDenegadoPage } from './AccesoDenegadoPage'

const NAV_ITEMS = [
  { to: '/', label: 'Inicio' },
  { to: '/carga', label: 'Carga' },
  { to: '/lista', label: 'Lista' },
  { to: '/campanias', label: 'Campañas' },
  { to: '/dashboard', label: 'Dashboard' },
] as const

function navLinkClass({ isActive }: { isActive: boolean }): string {
  const base =
    'rounded-pill px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'
  return isActive
    ? `${base} bg-brand text-surface shadow-sm`
    : `${base} text-muted hover:bg-brand/10 hover:text-ink`
}

/**
 * Marco comun de la aplicacion: cabecera con navegacion y contenido de la ruta hija. Si la API
 * responde `403 forbidden` (CU-00), muestra solo el aviso de acceso no permitido, sin menu.
 * Al imprimir (R-012) la cabecera no sale y el contenido va sin relleno.
 */
export function AppLayout() {
  const denegado = useSyncExternalStore(suscribir, estaDenegado)

  if (denegado) {
    return (
      <div className="min-h-screen bg-canvas font-sans text-ink">
        <main className="mx-auto w-full max-w-[96rem] px-4 py-12 sm:px-8">
          <AccesoDenegadoPage />
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-canvas font-sans text-ink print:bg-surface">
      <header className="sticky top-0 z-40 border-b border-line bg-surface/95 shadow-sm backdrop-blur print:hidden">
        <div className="mx-auto flex w-full max-w-[96rem] flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          {/* Marca: texto, no encabezado (el unico h1 es el de cada pagina). */}
          <span className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
            <span aria-hidden="true" className="size-2.5 rounded-pill bg-brand" />
            Mtabolic
          </span>
          <nav aria-label="Principal">
            <ul className="flex flex-wrap gap-1">
              {NAV_ITEMS.map(({ to, label }) => (
                <li key={to}>
                  <NavLink to={to} end={to === '/'} className={navLinkClass}>
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[96rem] px-4 py-8 sm:px-8 print:max-w-none print:p-0">
        <Suspense fallback={<LoadingIndicator />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}
