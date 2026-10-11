import type { InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { apiClient } from './client'
import {
  createEvent,
  deleteEvent,
  getEvent,
  listEvents,
  updateEvent,
  updateStatus,
} from './events'
import type { EventPayload } from '../types'

let sent: InternalAxiosRequestConfig | undefined
let answer: unknown

const payload: EventPayload = {
  name: 'PyCon',
  description: '',
  location: 'Medellín',
  start_at: '2030-05-20T09:00:00.000Z',
  end_at: '2030-05-21T18:00:00.000Z',
  capacity: 300,
}

beforeEach(() => {
  sent = undefined
  answer = { id: 7 }
  apiClient.defaults.adapter = async (config) => {
    sent = config
    return { status: 200, data: answer, statusText: '', headers: {}, config }
  }
})

describe('events api', () => {
  it('listEvents gets /events with the search and pagination params', async () => {
    answer = { items: [], total: 0, page: 2, size: 9, pages: 0 }
    const page = await listEvents({ q: 'py', page: 2, size: 9 })
    expect(sent?.method).toBe('get')
    expect(sent?.url).toBe('/events')
    expect(sent?.params).toEqual({ q: 'py', page: 2, size: 9 })
    expect(page.page).toBe(2)
  })

  it('getEvent gets /events/{id}', async () => {
    const event = await getEvent(7)
    expect(sent?.method).toBe('get')
    expect(sent?.url).toBe('/events/7')
    expect(event.id).toBe(7)
  })

  it('createEvent posts the payload to /events', async () => {
    await createEvent(payload)
    expect(sent?.method).toBe('post')
    expect(sent?.url).toBe('/events')
    expect(JSON.parse(sent?.data)).toEqual(payload)
  })

  it('updateEvent puts the payload to /events/{id}', async () => {
    await updateEvent(7, payload)
    expect(sent?.method).toBe('put')
    expect(sent?.url).toBe('/events/7')
    expect(JSON.parse(sent?.data)).toEqual(payload)
  })

  it('updateStatus patches the target status to /events/{id}/status', async () => {
    await updateStatus(7, 'published')
    expect(sent?.method).toBe('patch')
    expect(sent?.url).toBe('/events/7/status')
    expect(JSON.parse(sent?.data)).toEqual({ status: 'published' })
  })

  it('deleteEvent deletes /events/{id}', async () => {
    await deleteEvent(7)
    expect(sent?.method).toBe('delete')
    expect(sent?.url).toBe('/events/7')
  })
})
