import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listMyEvents, unregister } from '../api/registrations'
import { Button } from '../components/Button'
import { ErrorMessage } from '../components/ErrorMessage'
import { Pagination } from '../components/Pagination'
import { Spinner } from '../components/Spinner'
import { StatusBadge } from '../components/StatusBadge'
import { es, roleLabel } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { toast } from '../store/toastStore'
import type { Page, RegisteredEvent } from '../types'
import { formatDateTime } from '../utils/format'
import { canCancelRegistration } from '../utils/permissions'
import styles from './Pages.module.css'

const PAGE_SIZE = 10

/** What came back for one request; `key` says which request it answers. */
interface Outcome {
  key: string
  data: Page<RegisteredEvent> | null
  error: string | null
}

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user)
  const [page, setPage] = useState(1)
  // Bumped to load the same page again after cancelling a registration.
  const [reload, setReload] = useState(0)
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [cancelling, setCancelling] = useState(false)

  // The outcome is current only when it answers the page and reload counter being shown.
  const key = `${page}:${reload}`
  const current = outcome?.key === key ? outcome : null
  const items = current?.data?.items ?? []

  useEffect(() => {
    let active = true
    listMyEvents(page, PAGE_SIZE)
      .then((data) => active && setOutcome({ key, data, error: null }))
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : es.profile.loadFailed
        if (active) setOutcome({ key, data: null, error: message })
      })
    // A newer request makes this response stale: it must not overwrite the newer one.
    return () => {
      active = false
    }
  }, [page, key])

  async function handleCancel(event: RegisteredEvent) {
    setCancelling(true)
    try {
      await unregister(event.id)
      toast.success(es.profile.cancelled(event.name))
      // Cancelling the only item of a later page leaves it empty: show the previous one.
      if (items.length === 1 && page > 1) setPage(page - 1)
      else setReload((count) => count + 1)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : es.profile.cancelFailed)
    } finally {
      setCancelling(false)
    }
  }

  return (
    <section>
      <div className={styles.header}>
        <h1>{es.profile.title}</h1>
      </div>
      {user && (
        <>
          <h2 className={styles.fullName}>{user.full_name}</h2>
          <p className={styles.muted}>{es.profile.summary(user.email, roleLabel(user.role))}</p>
        </>
      )}
      {current === null && <Spinner />}
      <ErrorMessage message={current?.error} />
      {current?.data && items.length === 0 && (
        <p className={styles.muted}>
          {es.profile.empty} <Link to="/">{es.profile.browse}</Link>
        </p>
      )}
      {items.length > 0 && (
        <ul className={`${styles.panel} ${styles.list}`}>
          {items.map((event) => {
            const blocked = !canCancelRegistration(event.status)
            return (
              <li key={event.id} className={styles.row}>
                <div>
                  <Link to={`/events/${event.id}`}>{event.name}</Link>{' '}
                  <StatusBadge status={event.status} />
                  <div className={styles.muted}>{formatDateTime(event.start_at)}</div>
                  {blocked && (
                    <div className={styles.muted}>{es.events.cancelRegistrationClosed}</div>
                  )}
                </div>
                <Button
                  variant="secondary"
                  disabled={blocked || cancelling}
                  aria-label={es.profile.cancelAria(event.name)}
                  onClick={() => void handleCancel(event)}
                >
                  {es.profile.cancelRegistration}
                </Button>
              </li>
            )
          })}
        </ul>
      )}
      {/* Keeps the controls of the last loaded response while the next page is loading. */}
      <Pagination page={page} pages={outcome?.data?.pages ?? 0} onPageChange={setPage} />
    </section>
  )
}
