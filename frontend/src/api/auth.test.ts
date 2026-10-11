import type { InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { fetchMe, login, register } from './auth'
import { apiClient } from './client'

let sent: InternalAxiosRequestConfig | undefined

beforeEach(() => {
  sent = undefined
  apiClient.defaults.adapter = async (config) => {
    sent = config
    return { status: 200, data: { ok: true }, statusText: '', headers: {}, config }
  }
})

describe('auth api', () => {
  it('register posts the credentials to /auth/register', async () => {
    await register('ana@example.com', 'secret123')
    expect(sent?.method).toBe('post')
    expect(sent?.url).toBe('/auth/register')
    expect(JSON.parse(sent?.data)).toEqual({ email: 'ana@example.com', password: 'secret123' })
  })

  it('login posts the credentials to /auth/login', async () => {
    await login('ana@example.com', 'secret123')
    expect(sent?.url).toBe('/auth/login')
  })

  it('fetchMe gets /users/me', async () => {
    await fetchMe()
    expect(sent?.method).toBe('get')
    expect(sent?.url).toBe('/users/me')
  })
})
