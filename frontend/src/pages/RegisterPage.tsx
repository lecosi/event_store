import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../components/Button'
import { ErrorMessage } from '../components/ErrorMessage'
import { Input } from '../components/Input'
import { es } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { validateConfirmation, validateEmail, validatePassword } from '../utils/validation'
import styles from './AuthForm.module.css'

interface FieldErrors {
  email?: string | null
  password?: string | null
  confirm?: string | null
}

export default function RegisterPage() {
  const register = useAuthStore((s) => s.register)
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitError(null)

    const nextErrors: FieldErrors = {
      email: validateEmail(email),
      password: validatePassword(password),
      confirm: validateConfirmation(password, confirm),
    }
    setErrors(nextErrors)
    if (Object.values(nextErrors).some(Boolean)) return

    setSubmitting(true)
    try {
      // The store creates the account and then logs in with the same credentials.
      await register(email.trim(), password)
      navigate('/', { replace: true })
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : es.auth.register.failed)
      setSubmitting(false)
    }
  }

  return (
    <section className={styles.card}>
      <h1>{es.auth.register.title}</h1>
      <ErrorMessage message={submitError} />
      <form onSubmit={handleSubmit} noValidate>
        <Input
          label={es.fields.email}
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={errors.email}
        />
        <Input
          label={es.fields.password}
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
        />
        <Input
          label={es.auth.register.confirmPassword}
          type="password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          error={errors.confirm}
        />
        <Button type="submit" loading={submitting}>
          {es.auth.register.submit}
        </Button>
      </form>
      <p className={styles.footer}>
        {es.auth.register.alreadyRegistered} <Link to="/login">{es.auth.register.loginLink}</Link>
      </p>
    </section>
  )
}
