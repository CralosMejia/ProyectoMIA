import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { router } from './app/router'
import { config } from './core/config'
import './index.css'

/**
 * Arranca MSW en el navegador solo en desarrollo y con VITE_API_MOCKS=true.
 * El import dinamico bajo `import.meta.env.DEV` deja el worker fuera del build.
 */
async function enableMocking(): Promise<void> {
  if (import.meta.env.DEV && config.apiMocks) {
    const { worker } = await import('./mocks/browser')
    await worker.start({ onUnhandledRequest: 'bypass' })
  }
}

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('No se encontro el elemento #root')
}

void enableMocking().then(() => {
  createRoot(rootElement).render(
    <StrictMode>
      <RouterProvider router={router} />
    </StrictMode>,
  )
})
