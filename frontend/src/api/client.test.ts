import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { es } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { ApiError, apiClient, normalizeError } from './client'

let sentConfig: InternalAxiosRequestConfig | undefined

function respondWith(status: number, data: unknown) {
  apiClient.defaults.adapter = async (config) => {
    sentConfig = config
    const response = { status, data, statusText: '', headers: {}, config }
    if (status >= 400) throw new AxiosError('failed', 'ERR_BAD_REQUEST', config, null, response)
    return response
  }
}

function failWithoutResponse() {
  apiClient.defaults.adapter = async (config) => {
    throw new AxiosError('Network Error', 'ERR_NETWORK', config)
  }
}

async function errorOf(request: Promise<unknown>): Promise<ApiError> {
  try {
    await request
  } catch (error) {
    return error as ApiError
  }
  throw new Error('request did not fail')
}

beforeEach(() => {
  sentConfig = undefined
  useAuthStore.setState({ token: null, user: null })
})

describe('apiClient request interceptor', () => {
  it('sends the bearer token when the user is logged in', async () => {
    useAuthStore.setState({ token: 'abc' })
    respondWith(200, {})
    await apiClient.get('/events')
    expect(sentConfig?.headers.get('Authorization')).toBe('Bearer abc')
  })

  it('sends no authorization header when the user is logged out', async () => {
    respondWith(200, {})
    await apiClient.get('/events')
    expect(sentConfig?.headers.get('Authorization')).toBeUndefined()
  })
})

describe('apiClient response interceptor', () => {
  it('logs the user out when the backend answers 401', async () => {
    useAuthStore.setState({ token: 'expired' })
    respondWith(401, { detail: 'Could not validate credentials' })
    const error = await errorOf(apiClient.get('/users/me'))
    expect(error.status).toBe(401)
    expect(useAuthStore.getState().token).toBeNull()
  })

  it('keeps the session when the backend answers 403', async () => {
    useAuthStore.setState({ token: 'valid' })
    respondWith(403, { detail: 'Insufficient permissions' })
    await errorOf(apiClient.get('/events'))
    expect(useAuthStore.getState().token).toBe('valid')
  })

  it('rejects with an ApiError carrying the network message and no status when the server is unreachable', async () => {
    failWithoutResponse()
    const error = await errorOf(apiClient.get('/events'))
    expect(error).toBeInstanceOf(ApiError)
    expect(error.message).toBe(es.common.networkError)
    expect(error.status).toBeNull()
  })

  it('translates a known backend detail to Spanish', async () => {
    respondWith(404, { detail: 'Event not found' })
    const error = await errorOf(apiClient.get('/events/9'))
    expect(error.message).toBe('Evento no encontrado.')
    expect(error.status).toBe(404)
  })

  it('shows an unknown backend detail as is', async () => {
    respondWith(409, { detail: 'Something brand new happened' })
    const error = await errorOf(apiClient.post('/events'))
    expect(error.message).toBe('Something brand new happened')
  })

  it('uses the generic message when the response has no detail', async () => {
    respondWith(500, {})
    const error = await errorOf(apiClient.get('/events'))
    expect(error.message).toBe(es.common.genericError)
    expect(error.status).toBe(500)
  })

  it('prefixes each 422 item with the Spanish field label', async () => {
    respondWith(422, {
      detail: [
        { loc: ['body', 'email'], msg: 'value is not a valid email address', type: 'value_error' },
        { loc: ['body', 'capacity'], msg: 'Input should be greater than 0', type: 'greater_than' },
      ],
    })
    const error = await errorOf(apiClient.post('/events'))
    expect(error.message).toBe(
      'Correo electrónico: value is not a valid email address. Capacidad: Input should be greater than 0',
    )
  })

  it('shows the bare message for a 422 item whose field has no label', async () => {
    respondWith(422, { detail: [{ loc: ['body', 'unlisted'], msg: 'Field required', type: 'missing' }] })
    const error = await errorOf(apiClient.post('/events'))
    expect(error.message).toBe('Field required')
  })
})

describe('normalizeError', () => {
  it('returns an ApiError untouched', () => {
    const original = new ApiError('x', 400)
    expect(normalizeError(original)).toBe(original)
  })

  it('maps an unknown thrown value to the generic message', () => {
    expect(normalizeError(new Error('boom')).message).toBe(es.common.genericError)
  })
})
