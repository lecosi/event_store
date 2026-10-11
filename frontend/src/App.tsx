import { useEffect } from 'react'
import { RouterProvider } from 'react-router-dom'
import { router } from './routes'
import { useAuthStore } from './store/authStore'

export default function App() {
  // Restore the logged-in user from the persisted token once, on startup.
  useEffect(() => {
    void useAuthStore.getState().hydrate()
  }, [])

  return <RouterProvider router={router} />
}
