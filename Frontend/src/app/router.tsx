import { createBrowserRouter } from 'react-router-dom'
import { healthRoutes } from '../features/health/routes'

export const router = createBrowserRouter([...healthRoutes])
