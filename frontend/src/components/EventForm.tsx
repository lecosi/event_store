import { useState, type FormEvent } from 'react'
import { es } from '../i18n'
import type { EventPayload } from '../types'
import {
  parseCapacity,
  validateEventForm,
  type EventFormValues,
  type FormErrors,
} from '../utils/eventValidation'
import { fromInputValue, toInputValue } from '../utils/format'
import { Button } from './Button'
import { ErrorMessage } from './ErrorMessage'
import { TextArea } from './Fields'
import { Input } from './Input'
import styles from './Form.module.css'

interface EventFormProps {
  /** Present when editing: the form starts with these values. */
  initial?: EventPayload
  submitLabel: string
  /** Only a new event must start in the future. */
  requireFutureStart: boolean
  /** A rejection is shown above the form (for example the backend 422/409 message). */
  onSubmit: (payload: EventPayload) => Promise<void>
}

function toValues(initial?: EventPayload): EventFormValues {
  if (!initial) {
    return { name: '', description: '', location: '', start_at: '', end_at: '', capacity: '' }
  }
  return {
    name: initial.name,
    description: initial.description,
    location: initial.location,
    start_at: toInputValue(initial.start_at),
    end_at: toInputValue(initial.end_at),
    capacity: String(initial.capacity),
  }
}

export function EventForm({ initial, submitLabel, requireFutureStart, onSubmit }: EventFormProps) {
  const [values, setValues] = useState<EventFormValues>(() => toValues(initial))
  const [errors, setErrors] = useState<FormErrors<EventFormValues>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const bind = (field: keyof EventFormValues) => ({
    value: values[field],
    error: errors[field],
    onChange: (e: { target: { value: string } }) =>
      setValues((current) => ({ ...current, [field]: e.target.value })),
  })

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitError(null)
    const nextErrors = validateEventForm(values, { requireFuture: requireFutureStart })
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    try {
      await onSubmit({
        name: values.name.trim(),
        description: values.description,
        location: values.location.trim(),
        start_at: fromInputValue(values.start_at),
        end_at: fromInputValue(values.end_at),
        capacity: parseCapacity(values.capacity),
      })
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : es.events.form.saveFailed)
      setSubmitting(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <ErrorMessage message={submitError} />
      <Input label={es.fields.name} {...bind('name')} />
      <TextArea label={es.fields.description} {...bind('description')} />
      <Input label={es.fields.location} {...bind('location')} />
      <div className={styles.row}>
        <Input label={es.fields.start_at} type="datetime-local" {...bind('start_at')} />
        <Input label={es.fields.end_at} type="datetime-local" {...bind('end_at')} />
      </div>
      <Input label={es.fields.capacity} type="number" min={1} {...bind('capacity')} />
      <Button type="submit" loading={submitting}>
        {submitLabel}
      </Button>
    </form>
  )
}
