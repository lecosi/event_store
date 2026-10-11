import { useState, type FormEvent } from 'react'
import { updateUser } from '../api/admin'
import { es, roleLabel } from '../i18n'
import type { Role, User, UserUpdatePayload } from '../types'
import { validateEmail, validateFullName } from '../utils/validation'
import { Button } from './Button'
import { ErrorMessage } from './ErrorMessage'
import { Input } from './Input'
import { Select } from './Fields'
import styles from './UserEditForm.module.css'

const ROLES: Role[] = ['admin', 'organizer', 'attendee']

interface UserEditFormProps {
  user: User
  /** The logged-in admin cannot demote or deactivate themselves (the backend answers 409). */
  isOwnAccount: boolean
  onSaved: (user: User) => void
  onCancel: () => void
}

/** Edits one user and sends only the fields that changed. */
export function UserEditForm({ user, isOwnAccount, onSaved, onCancel }: UserEditFormProps) {
  const [fullName, setFullName] = useState(user.full_name)
  const [email, setEmail] = useState(user.email)
  const [role, setRole] = useState<Role>(user.role)
  const [isActive, setIsActive] = useState(user.is_active)
  const [errors, setErrors] = useState<{ fullName?: string; email?: string }>({})
  const [hint, setHint] = useState<string | null>(null)
  const [requestError, setRequestError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setHint(null)
    setRequestError(null)

    const nextErrors = {
      fullName: validateFullName(fullName) ?? undefined,
      email: validateEmail(email) ?? undefined,
    }
    setErrors(nextErrors)
    if (nextErrors.fullName || nextErrors.email) return

    const payload: UserUpdatePayload = {}
    if (fullName.trim() !== user.full_name) payload.full_name = fullName.trim()
    if (email.trim().toLowerCase() !== user.email) payload.email = email.trim()
    if (role !== user.role) payload.role = role
    if (isActive !== user.is_active) payload.is_active = isActive
    if (Object.keys(payload).length === 0) {
      setHint(es.admin.noChanges)
      return
    }

    setSaving(true)
    try {
      onSaved(await updateUser(user.id, payload))
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : es.admin.saveFailed)
      setSaving(false)
    }
  }

  return (
    <form
      className={styles.form}
      aria-label={es.admin.editAria(user.full_name)}
      onSubmit={(event) => void handleSubmit(event)}
      noValidate
    >
      <Input
        label={es.admin.fullName}
        value={fullName}
        error={errors.fullName}
        onChange={(event) => setFullName(event.target.value)}
      />
      <Input
        label={es.admin.email}
        type="email"
        value={email}
        error={errors.email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <Select
        label={es.admin.role}
        value={role}
        disabled={isOwnAccount}
        onChange={(event) => setRole(event.target.value as Role)}
      >
        {ROLES.map((value) => (
          <option key={value} value={value}>
            {roleLabel(value)}
          </option>
        ))}
      </Select>
      <label className={styles.check}>
        <input
          type="checkbox"
          checked={isActive}
          disabled={isOwnAccount}
          onChange={(event) => setIsActive(event.target.checked)}
        />
        {es.admin.isActive}
      </label>
      {isOwnAccount && <p className={styles.hint}>{es.admin.ownAccountHint}</p>}
      <ErrorMessage message={requestError} />
      <div aria-live="polite">{hint && <p className={styles.hint}>{hint}</p>}</div>
      <div className={styles.actions}>
        <Button type="submit" loading={saving}>
          {es.admin.save}
        </Button>
        <Button variant="secondary" onClick={onCancel}>
          {es.common.cancel}
        </Button>
      </div>
    </form>
  )
}
