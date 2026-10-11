import { lazy } from 'react'
import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { ProtectedRoute } from './ProtectedRoute'

// Each page is its own chunk, downloaded the first time its route is visited.
const EventListPage = lazy(() => import('../pages/EventListPage'))
const EventDetailPage = lazy(() => import('../pages/EventDetailPage'))
const EventFormPage = lazy(() => import('../pages/EventFormPage'))
const SpeakerFormPage = lazy(() => import('../pages/SpeakerFormPage'))
const ProfilePage = lazy(() => import('../pages/ProfilePage'))
const AdminUsersPage = lazy(() => import('../pages/AdminUsersPage'))
const ReportsPage = lazy(() => import('../pages/ReportsPage'))
const LoginPage = lazy(() => import('../pages/LoginPage'))
const RegisterPage = lazy(() => import('../pages/RegisterPage'))
const NotFoundPage = lazy(() => import('../pages/NotFoundPage'))

/** Exported separately so tests can mount it with createMemoryRouter. */
export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: '/', element: <EventListPage /> },
      { path: '/events/:id', element: <EventDetailPage /> },
      {
        element: <ProtectedRoute />,
        children: [
          { path: '/events/new', element: <EventFormPage /> },
          { path: '/events/:id/edit', element: <EventFormPage /> },
          { path: '/speakers/new', element: <SpeakerFormPage /> },
          { path: '/profile', element: <ProfilePage /> },
          { path: '/admin/users', element: <AdminUsersPage /> },
          { path: '/reports', element: <ReportsPage /> },
        ],
      },
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
