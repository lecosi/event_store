import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { es } from '../i18n'
import type { Event, Session, SessionPayload, SpeakerRef } from '../types'
import {
  parseCapacity,
  validateSessionForm,
  type FormErrors,
  type SessionFormValues,
} from '../utils/eventValidation'
import { fromInputValue, toInputValue } from '../utils/format'
import { Button } from './Button'
import { ErrorMessage } from './ErrorMessage'
import { Input } from './Input'
import { SpeakerPicker } from './SpeakerPicker'
import styles from './Form.module.css'

interface SessionFormProps {
  /** The event the session belongs to: its dates and capacity bound the session. */
  event: Pick<Event, 'start_at' | 'end_at' | 'capacity'>
  /** Present when editing: the form starts with these values. */
  session?: Session
  /** A rejection is shown above the form (for example the backend 409 for a speaker clash). */
  onSubmit: (payload: SessionPayload) => Promise<void>
  onCancel: () => void
}

export function SessionForm({ event, session, onSubmit, onCancel }: SessionFormProps) {
  const [values, setValues] = useState<SessionFormValues>(() => ({
    title: session?.title ?? '',
    speaker_id: session ? String(session.speaker.id) : '',
    start_at: session ? toInputValue(session.start_at) : '',
    end_at: session ? toInputValue(session.end_at) : '',
    capacity: session ? String(session.capacity) : '',
  }))
  const [speaker, setSpeaker] = useState<SpeakerRef | null>(session?.speaker ?? null)
  const [errors, setErrors] = useState<FormErrors<SessionFormValues>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const bind = (field: keyof SessionFormValues) => ({
    value: values[field],
    error: errors[field],
    onChange: (e: { target: { value: string } }) =>
      setValues((current) => ({ ...current, [field]: e.target.value })),
  })

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitError(null)
    const nextErrors = validateSessionForm(values, event)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    try {
      await onSubmit({
        title: values.title.trim(),
        speaker_id: Number(values.speaker_id),
        start_at: fromInputValue(values.start_at),
        end_at: fromInputValue(values.end_at),
        capacity: parseCapacity(values.capacity),
      })
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : es.sessions.saveFailed)
      setSubmitting(false)
    }
  }

  return (
    <form
      className={styles.form}
      onSubmit={handleSubmit}
      noValidate
      aria-label={es.sessions.formLabel}
    >
      <ErrorMessage message={submitError} />
      <Input label={es.sessions.title} {...bind('title')} />
      <SpeakerPicker
        selected={speaker}
        error={errors.speaker_id}
        onSelect={(chosen) => {
          setSpeaker(chosen)
          setValues((current) => ({ ...current, speaker_id: String(chosen.id) }))
        }}
      />
      <p>
        <Link to="/speakers/new">{es.sessions.newSpeaker}</Link>
      </p>
      <div className={styles.row}>
        <Input label={es.sessions.starts} type="datetime-local" {...bind('start_at')} />
        <Input label={es.sessions.ends} type="datetime-local" {...bind('end_at')} />
      </div>
      <Input label={es.sessions.capacity} type="number" min={1} {...bind('capacity')} />
      <div className={styles.actions}>
        <Button type="submit" loading={submitting}>
          {session ? es.sessions.save : es.sessions.add}
        </Button>
        <Button variant="secondary" onClick={onCancel}>
          {es.common.cancel}
        </Button>
      </div>
    </form>
  )
}
