import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

/** Service worker MSW para desarrollo local (solo con VITE_API_MOCKS=true). */
export const worker = setupWorker(...handlers)
