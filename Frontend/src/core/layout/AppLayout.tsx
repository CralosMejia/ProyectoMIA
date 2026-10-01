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
  const base = 'rounded-pill px-4 py-2 text-sm font-medium'
  return isActive ? `${base} bg-ink text-surface` : `${base} text-ink hover:bg-ink/10`
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
      <div className="min-h-screen bg-surface font-sans text-ink">
        <main className="p-8">
          <AccesoDenegadoPage />
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface font-sans text-ink">
      <header className="border-b border-ink/10 px-8 py-4 print:hidden">
        <nav aria-label="Principal">
          <ul className="flex flex-wrap gap-2">
            {NAV_ITEMS.map(({ to, label }) => (
              <li key={to}>
                <NavLink to={to} end={to === '/'} className={navLinkClass}>
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main className="p-8 print:p-0">
        <Suspense fallback={<LoadingIndicator />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}
