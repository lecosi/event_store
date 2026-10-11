import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { es } from '../i18n'
import type { SpeakerPayload } from '../types'
import type { FormErrors } from '../utils/eventValidation'
import { validateSpeakerForm, type SpeakerFormValues } from '../utils/speakerValidation'
import { Button } from './Button'
import { ErrorMessage } from './ErrorMessage'
import { TextArea } from './Fields'
import { Input } from './Input'
import styles from './Form.module.css'

interface SpeakerFormProps {
  /** A rejection is shown above the form; a 409 (email taken) is shown on the email field. */
  onSubmit: (payload: SpeakerPayload) => Promise<void>
}

export function SpeakerForm({ onSubmit }: SpeakerFormProps) {
  const [values, setValues] = useState<SpeakerFormValues>({ name: '', bio: '', email: '' })
  const [errors, setErrors] = useState<FormErrors<SpeakerFormValues>>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const bind = (field: keyof SpeakerFormValues) => ({
    value: values[field],
    error: errors[field],
    onChange: (e: { target: { value: string } }) =>
      setValues((current) => ({ ...current, [field]: e.target.value })),
  })

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitError(null)
    const nextErrors = validateSpeakerForm(values)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    setSubmitting(true)
    const email = values.email.trim()
    try {
      // The backend rejects an empty string as an email, so a blank one is left out.
      await onSubmit({ name: values.name.trim(), bio: values.bio, ...(email ? { email } : {}) })
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setErrors({ email: error.message })
      } else {
        setSubmitError(error instanceof Error ? error.message : es.speakers.createFailed)
      }
      setSubmitting(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <ErrorMessage message={submitError} />
      <Input label={es.fields.name} {...bind('name')} />
      <TextArea label={es.fields.bio} {...bind('bio')} />
      <Input label={es.fields.email} type="email" {...bind('email')} />
      <Button type="submit" loading={submitting}>
        {es.speakers.create}
      </Button>
    </form>
  )
}
