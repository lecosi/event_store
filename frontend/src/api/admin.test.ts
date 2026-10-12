import type { InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it } from 'vitest'
import { listUsers, updateUser } from './admin'
import { apiClient } from './client'

let sent: InternalAxiosRequestConfig | undefined
let answer: unknown

beforeEach(() => {
  sent = undefined
  answer = { id: 7 }
  apiClient.defaults.adapter = async (config) => {
    sent = config
    return { status: 200, data: answer, statusText: '', headers: {}, config }
  }
})

describe('admin api', () => {
  it('listUsers gets /admin/users with the pagination params', async () => {
    answer = { items: [], total: 0, page: 2, size: 10, pages: 0 }
    const page = await listUsers({ page: 2, size: 10 })
    expect(sent?.method).toBe('get')
    expect(sent?.url).toBe('/admin/users')
    expect(sent?.params).toEqual({ page: 2, size: 10 })
    expect(page.page).toBe(2)
  })

  it('listUsers sends the email prefix as a query param', async () => {
    answer = { items: [], total: 0, page: 1, size: 10, pages: 0 }
    await listUsers({ email: 'ana', page: 1, size: 10 })
    expect(sent?.params).toEqual({ email: 'ana', page: 1, size: 10 })
  })

  it('updateUser patches /admin/users/{id} with only the given fields', async () => {
    const user = await updateUser(7, { email: 'nuevo@example.com' })
    expect(sent?.method).toBe('patch')
    expect(sent?.url).toBe('/admin/users/7')
    expect(JSON.parse(sent?.data)).toEqual({ email: 'nuevo@example.com' })
    expect(user.id).toBe(7)
  })
})
