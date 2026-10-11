import { lazy } from 'react'
import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { Layout } from '../components/Layout'

// Each page is its own chunk, downloaded the first time its route is visited.
const EventListPage = lazy(() => import('../pages/EventListPage'))
const EventDetailPage = lazy(() => import('../pages/EventDetailPage'))
const NotFoundPage = lazy(() => import('../pages/NotFoundPage'))

/** Exported separately so tests can mount it with createMemoryRouter. */
export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: '/', element: <EventListPage /> },
      { path: '/events/:id', element: <EventDetailPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
