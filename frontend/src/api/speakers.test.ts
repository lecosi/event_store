import type { InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { apiClient } from './client'
import { createSpeaker, listSpeakers } from './speakers'

let sent: InternalAxiosRequestConfig | undefined
let answer: unknown

beforeEach(() => {
  sent = undefined
  answer = { id: 3, name: 'Grace Hopper', bio: '', email: null }
  apiClient.defaults.adapter = async (config) => {
    sent = config
    return { status: 200, data: answer, statusText: '', headers: {}, config }
  }
})

describe('speakers api', () => {
  it('listSpeakers gets /speakers with the search and pagination params', async () => {
    answer = { items: [], total: 0, page: 1, size: 10, pages: 0 }
    const page = await listSpeakers({ q: 'gra', size: 10 })
    expect(sent?.method).toBe('get')
    expect(sent?.url).toBe('/speakers')
    expect(sent?.params).toEqual({ q: 'gra', size: 10 })
    expect(page.items).toEqual([])
  })

  it('createSpeaker posts the payload to /speakers and returns the speaker', async () => {
    const speaker = await createSpeaker({ name: 'Grace Hopper', bio: '' })
    expect(sent?.method).toBe('post')
    expect(sent?.url).toBe('/speakers')
    expect(JSON.parse(sent?.data as string)).toEqual({ name: 'Grace Hopper', bio: '' })
    expect(speaker.id).toBe(3)
  })
})
