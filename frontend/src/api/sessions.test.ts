import type { InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { apiClient } from './client'
import { createSession, deleteSession, updateSession } from './sessions'
import type { SessionPayload } from '../types'

let sent: InternalAxiosRequestConfig | undefined

const payload: SessionPayload = {
  title: 'Apertura',
  speaker_id: 3,
  start_at: '2030-05-20T10:00:00.000Z',
  end_at: '2030-05-20T11:00:00.000Z',
  capacity: 50,
}

beforeEach(() => {
  sent = undefined
  apiClient.defaults.adapter = async (config) => {
    sent = config
    return { status: 200, data: { id: 9 }, statusText: '', headers: {}, config }
  }
})

describe('sessions api', () => {
  it('createSession posts the payload to /events/{id}/sessions', async () => {
    const session = await createSession(5, payload)
    expect(sent?.method).toBe('post')
    expect(sent?.url).toBe('/events/5/sessions')
    expect(JSON.parse(sent?.data as string)).toEqual(payload)
    expect(session.id).toBe(9)
  })

  it('updateSession puts the payload to /events/{id}/sessions/{sid}', async () => {
    await updateSession(5, 9, payload)
    expect(sent?.method).toBe('put')
    expect(sent?.url).toBe('/events/5/sessions/9')
    expect(JSON.parse(sent?.data as string)).toEqual(payload)
  })

  it('deleteSession deletes /events/{id}/sessions/{sid}', async () => {
    await deleteSession(5, 9)
    expect(sent?.method).toBe('delete')
    expect(sent?.url).toBe('/events/5/sessions/9')
  })
})
