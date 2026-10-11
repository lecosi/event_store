import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import { Navbar } from './Navbar'
import { Spinner } from './Spinner'
import { ToastContainer } from './Toast'
import styles from './Layout.module.css'

/** App shell: navbar on top, active page below. Pages are lazy, hence the Suspense. */
export function Layout() {
  return (
    <>
      <Navbar />
      <main className={styles.main}>
        <Suspense fallback={<Spinner />}>
          <Outlet />
        </Suspense>
      </main>
      <ToastContainer />
    </>
  )
}
