import { useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { createEvent, updateEvent } from '../api/events'
import { ErrorMessage } from '../components/ErrorMessage'
import { EventForm } from '../components/EventForm'
import { Spinner } from '../components/Spinner'
import { es } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { useEventStore } from '../store/eventStore'
import { toast } from '../store/toastStore'
import type { EventPayload } from '../types'
import { canCreateEvents, canManageEvent } from '../utils/permissions'

/** Serves both /events/new (create) and /events/:id/edit (edit). */
export default function EventFormPage() {
  const rawId = useParams().id
  const editingId = rawId === undefined ? null : Number(rawId)
  const validEditId = editingId !== null && Number.isInteger(editingId) && editingId > 0
  const navigate = useNavigate()

  const user = useAuthStore((s) => s.user)
  const { currentEvent, detailLoading, detailError, fetchEvent, clearCurrent } = useEventStore()

  useEffect(() => {
    if (!validEditId) return
    void fetchEvent(editingId)
    return clearCurrent
  }, [editingId, validEditId, fetchEvent, clearCurrent])

  // A rejection propagates to EventForm, which shows the backend message.
  async function handleSubmit(payload: EventPayload) {
    const saved =
      editingId === null ? await createEvent(payload) : await updateEvent(editingId, payload)
    toast.success(editingId === null ? es.events.form.created : es.events.form.updated)
    navigate(`/events/${saved.id}`)
  }

  // After a reload the profile arrives later; do not flash "not allowed" before it does.
  if (!user) return <Spinner />
  if (!canCreateEvents(user)) return <ErrorMessage message={es.events.form.notAllowed} />

  if (editingId === null) {
    return (
      <section>
        <h1>{es.events.form.newTitle}</h1>
        <EventForm submitLabel={es.events.form.create} requireFutureStart onSubmit={handleSubmit} />
      </section>
    )
  }

  if (!validEditId) return <ErrorMessage message={es.events.invalidId} />
  const event = currentEvent?.id === editingId ? currentEvent : null
  if (detailLoading && !event) return <Spinner />
  if (!event) return <ErrorMessage message={detailError ?? es.events.notFound} />
  if (!canManageEvent(user, event)) return <ErrorMessage message={es.events.form.notAllowedEdit} />

  return (
    <section>
      <h1>{es.events.form.editTitle}</h1>
      <p>
        <Link to={`/events/${event.id}`}>{es.events.form.back}</Link>
      </p>
      <EventForm
        initial={event}
        submitLabel={es.events.form.save}
        requireFutureStart={false}
        onSubmit={handleSubmit}
      />
    </section>
  )
}
