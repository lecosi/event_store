import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '../components/Button'
import { ErrorMessage } from '../components/ErrorMessage'
import { Input } from '../components/Input'
import { es } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { validateEmail, validatePassword } from '../utils/validation'
import styles from './AuthForm.module.css'

interface LocationState {
  from?: { pathname: string; search?: string }
}

export default function LoginPage() {
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()
  // ProtectedRoute (and the detail page) leave the requested location here.
  const from = (useLocation().state as LocationState | null)?.from
  const redirectTo = from ? `${from.pathname}${from.search ?? ''}` : '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string | null; password?: string | null }>({})
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitError(null)

    const nextErrors = { email: validateEmail(email), password: validatePassword(password) }
    setErrors(nextErrors)
    if (nextErrors.email || nextErrors.password) return

    setSubmitting(true)
    try {
      await login(email.trim(), password)
      navigate(redirectTo, { replace: true })
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : es.auth.login.failed)
      setSubmitting(false)
    }
  }

  return (
    <section className={styles.card}>
      <h1>{es.auth.login.title}</h1>
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
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
        />
        <Button type="submit" loading={submitting}>
          {es.auth.login.submit}
        </Button>
      </form>
      <p className={styles.footer}>
        {es.auth.login.noAccount} <Link to="/register">{es.auth.login.registerLink}</Link>
      </p>
    </section>
  )
}
