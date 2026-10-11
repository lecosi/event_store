import { lazy } from 'react'
import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { Layout } from '../components/Layout'

// Each page is its own chunk, downloaded the first time its route is visited.
const NotFoundPage = lazy(() => import('../pages/NotFoundPage'))

/** Exported separately so tests can mount it with createMemoryRouter. */
export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [{ path: '*', element: <NotFoundPage /> }],
  },
]

export const router = createBrowserRouter(routes)
