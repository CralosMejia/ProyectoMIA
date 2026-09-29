import { setupServer } from 'msw/node'
import { handlers } from './handlers'

/** Servidor MSW para pruebas (Node). */
export const server = setupServer(...handlers)
