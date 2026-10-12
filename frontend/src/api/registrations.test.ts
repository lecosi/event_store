import type { InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { apiClient } from './client'
import {
  cancelSessionEnrollment,
  enrollInSession,
  listMyEvents,
  register,
  unregister,
} from './registrations'

let sent: InternalAxiosRequestConfig | undefined

beforeEach(() => {
  sent = undefined
  apiClient.defaults.adapter = async (config) => {
    sent = config
    return { status: 200, data: { items: [] }, statusText: '', headers: {}, config }
  }
})

describe('registrations api', () => {
  it('register posts to /events/{id}/register', async () => {
    await register(4)
    expect(sent?.method).toBe('post')
    expect(sent?.url).toBe('/events/4/register')
  })

  it('unregister deletes /events/{id}/register', async () => {
    await unregister(4)
    expect(sent?.method).toBe('delete')
    expect(sent?.url).toBe('/events/4/register')
  })

  it('enrollInSession posts to /events/{id}/sessions/{id}/register', async () => {
    await enrollInSession(4, 9)
    expect(sent?.method).toBe('post')
    expect(sent?.url).toBe('/events/4/sessions/9/register')
  })

  it('cancelSessionEnrollment deletes /events/{id}/sessions/{id}/register', async () => {
    await cancelSessionEnrollment(4, 9)
    expect(sent?.method).toBe('delete')
    expect(sent?.url).toBe('/events/4/sessions/9/register')
  })

  it('listMyEvents gets /users/me/events with the pagination params', async () => {
    await listMyEvents(2, 5)
    expect(sent?.method).toBe('get')
    expect(sent?.url).toBe('/users/me/events')
    expect(sent?.params).toEqual({ page: 2, size: 5 })
  })
})
