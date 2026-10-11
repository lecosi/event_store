import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { deleteEvent, updateStatus } from '../api/events'
import { register, unregister } from '../api/registrations'
import { Button } from '../components/Button'
import { ErrorMessage } from '../components/ErrorMessage'
import { Select } from '../components/Fields'
import { Spinner } from '../components/Spinner'
import { StatusBadge } from '../components/StatusBadge'
import { es, statusLabel } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { useEventStore } from '../store/eventStore'
import { toast } from '../store/toastStore'
import type { EventStatus } from '../types'
import { formatDateTime } from '../utils/format'
import { canManageEvent, nextStatuses } from '../utils/permissions'
import styles from './Pages.module.css'

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : es.common.genericError
}

export default function EventDetailPage() {
  const id = Number(useParams().id)
  const validId = Number.isInteger(id) && id > 0
  const navigate = useNavigate()
  const location = useLocation()

  const user = useAuthStore((s) => s.user)
  const token = useAuthStore((s) => s.token)
  const { currentEvent, detailLoading, detailError, fetchEvent, clearCurrent } = useEventStore()

  const [busy, setBusy] = useState(false)
  const [newStatus, setNewStatus] = useState('')

  useEffect(() => {
    if (!validId) return
    void fetchEvent(id)
    return clearCurrent
  }, [id, validId, fetchEvent, clearCurrent])

  // Ignore a stale event left in the store by another page.
  const event = currentEvent?.id === id ? currentEvent : null

  /** Runs an API action, reports the result with a toast and reloads the event. */
  async function run(action: () => Promise<unknown>, successMessage: string): Promise<boolean> {
    setBusy(true)
    try {
      await action()
      toast.success(successMessage)
      await fetchEvent(id)
      return true
    } catch (error) {
      toast.error(messageOf(error))
      return false
    } finally {
      setBusy(false)
    }
  }

  function handleRegistration() {
    if (!event) return
    if (!token) {
      navigate('/login', { state: { from: location } })
      return
    }
    if (event.is_registered) void run(() => unregister(id), es.events.registrationCancelled)
    else void run(() => register(id), es.events.registered)
  }

  async function handleApplyStatus() {
    const target = newStatus as EventStatus
    const changed = await run(() => updateStatus(id, target), es.events.statusChanged(statusLabel(target)))
    if (changed) setNewStatus('')
  }

  async function handleDelete() {
    if (!window.confirm(es.events.confirmDelete)) return
    setBusy(true)
    try {
      await deleteEvent(id)
      toast.success(es.events.deleted)
      navigate('/')
    } catch (error) {
      toast.error(messageOf(error))
      setBusy(false)
    }
  }

  if (!validId) return <ErrorMessage message={es.events.invalidId} />
  if (detailLoading && !event) return <Spinner />
  if (!event) return <ErrorMessage message={detailError ?? es.events.notFound} />

  const canManage = canManageEvent(user, event)
  const statusOptions = nextStatuses(event.status)
  const registerDisabled =
    !event.is_registered && (event.status !== 'published' || event.available_spots <= 0)
  const sessions = [...event.sessions].sort((a, b) => a.start_at.localeCompare(b.start_at))

  return (
    <article>
      <div className={styles.header}>
        <h1>{event.name}</h1>
        <StatusBadge status={event.status} />
      </div>

      <section className={styles.panel} aria-label={es.events.infoLabel}>
        <p>{event.description || es.events.noDescription}</p>
        <p>
          <strong>{es.events.when}</strong> {formatDateTime(event.start_at)} -{' '}
          {formatDateTime(event.end_at)}
        </p>
        <p>
          <strong>{es.events.where}</strong> <span>{event.location}</span>
        </p>
        <p>
          <strong>{es.events.spotsLabel}</strong>{' '}
          <span>{es.events.spotsAvailable(event.available_spots, event.capacity)}</span>
        </p>

        <div className={styles.actions}>
          <Button
            variant={event.is_registered ? 'secondary' : 'primary'}
            loading={busy}
            disabled={registerDisabled}
            onClick={handleRegistration}
          >
            {event.is_registered ? es.events.cancelRegistration : es.events.register}
          </Button>
          {registerDisabled && (
            <span className={styles.muted}>
              {event.status !== 'published' ? es.events.registrationClosed : es.events.full}
            </span>
          )}
        </div>
      </section>

      {canManage && (
        <section className={styles.panel} aria-label={es.events.manageLabel}>
          <div className={styles.actions}>
            <Link to={`/events/${event.id}/edit`}>{es.events.edit}</Link>
            {statusOptions.length > 0 && (
              <>
                <Select
                  label={es.events.changeStatus}
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                >
                  <option value="">{es.events.selectStatus}</option>
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>
                      {statusLabel(status)}
                    </option>
                  ))}
                </Select>
                <Button
                  variant="secondary"
                  disabled={!newStatus || busy}
                  onClick={() => void handleApplyStatus()}
                >
                  {es.events.applyStatus}
                </Button>
              </>
            )}
            <Button variant="danger" disabled={busy} onClick={() => void handleDelete()}>
              {es.events.delete}
            </Button>
          </div>
        </section>
      )}

      <section className={styles.panel} aria-label={es.sessions.heading}>
        <h2>{es.sessions.heading}</h2>
        {sessions.length === 0 ? (
          <p className={styles.muted}>{es.sessions.empty}</p>
        ) : (
          <ul className={styles.list}>
            {sessions.map((session) => (
              <li key={session.id} className={styles.row}>
                <span>
                  <strong>{session.title}</strong> · {session.speaker.name}
                </span>
                <span className={styles.muted}>
                  {formatDateTime(session.start_at)} - {formatDateTime(session.end_at)} ·{' '}
                  {es.sessions.seats(session.capacity)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  )
}
