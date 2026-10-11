import axios, { AxiosError } from 'axios'
import { es } from '../i18n'
import { useAuthStore } from '../store/authStore'

/** Error thrown by every API call, with a message that is safe to show to users. */
export class ApiError extends Error {
  /** HTTP status, or null when the server could not be reached. */
  readonly status: number | null

  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface ValidationItem {
  loc?: (string | number)[]
  msg?: string
}

/** FastAPI 422 `detail` is a list of {loc, msg}; one sentence per item, prefixed by the field label. */
function formatValidation(items: ValidationItem[]): string {
  return items
    .map(({ loc = [], msg = es.common.invalidValue }) => {
      // loc looks like ['body', 'email']; the first element is the source, not useful to users.
      const label = es.fields[loc.slice(1).join('.')]
      return label ? `${label}: ${msg}` : msg
    })
    .join('. ')
}

/** Converts anything thrown by axios into an ApiError with a message for users. */
export function normalizeError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (error instanceof AxiosError) {
    if (!error.response) return new ApiError(es.common.networkError)
    const { status, data } = error.response
    const detail = (data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return new ApiError(es.errors.static[detail] ?? detail, status)
    if (Array.isArray(detail) && detail.length > 0) {
      return new ApiError(formatValidation(detail as ValidationItem[]), status)
    }
    return new ApiError(es.common.genericError, status)
  }
  return new ApiError(es.common.genericError)
}

/** Single axios instance shared by all API modules. */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
})

// Attach the JWT to every request when the user is logged in.
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.set('Authorization', `Bearer ${token}`)
  return config
})

// Normalize errors; an expired/invalid token (401) logs the user out.
apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const apiError = normalizeError(error)
    if (apiError.status === 401) useAuthStore.getState().logout()
    return Promise.reject(apiError)
  },
)
