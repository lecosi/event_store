import { Link, NavLink } from 'react-router-dom'
import { es } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { canCreateEvents } from '../utils/permissions'
import { Button } from './Button'
import styles from './Navbar.module.css'

export function Navbar() {
  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  return (
    <header className={styles.navbar}>
      <Link to="/" className={styles.brand}>
        {es.brand}
      </Link>
      <nav className={styles.links}>
        {token ? (
          <>
            {canCreateEvents(user) && (
              <NavLink to="/events/new" className={styles.cta}>
                {es.nav.newEvent}
              </NavLink>
            )}
            {canCreateEvents(user) && <NavLink to="/speakers/new">{es.nav.newSpeaker}</NavLink>}
            <NavLink to="/profile">{es.nav.myEvents}</NavLink>
            {user && <span className={styles.email}>{user.email}</span>}
            <Button variant="secondary" onClick={logout}>
              {es.nav.logout}
            </Button>
          </>
        ) : (
          <>
            <NavLink to="/login">{es.nav.login}</NavLink>
            <NavLink to="/register">{es.nav.register}</NavLink>
          </>
        )}
      </nav>
    </header>
  )
}
