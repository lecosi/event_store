import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as authApi from '../api/auth'
import type { User } from '../types'

vi.mock('../api/auth')

const user: User = {
  id: 1,
  email: 'ana@example.com',
  full_name: 'Ana Pérez',
  role: 'attendee',
  is_active: true,
}

async function freshStore() {
  vi.resetModules()
  const module = await import('./authStore')
  return module.useAuthStore
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.restoreAllMocks()
})

describe('authStore', () => {
  it('starts with the token persisted in localStorage', async () => {
    localStorage.setItem('auth_token', 'saved')
    const store = await freshStore()
    expect(store.getState().token).toBe('saved')
  })

  it('starts logged out when localStorage cannot be read', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const store = await freshStore()
    expect(store.getState().token).toBeNull()
  })

  it('login persists the token and loads the user', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'tok', token_type: 'bearer' })
    vi.mocked(authApi.fetchMe).mockResolvedValue(user)
    const store = await freshStore()
    await store.getState().login(user.email, 'secret123')
    expect(store.getState().token).toBe('tok')
    expect(store.getState().user).toEqual(user)
    expect(localStorage.getItem('auth_token')).toBe('tok')
  })

  it('login logs out and rethrows when the profile cannot be loaded', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'tok', token_type: 'bearer' })
    vi.mocked(authApi.fetchMe).mockRejectedValue(new Error('profile failed'))
    const store = await freshStore()
    await expect(store.getState().login(user.email, 'secret123')).rejects.toThrow('profile failed')
    expect(store.getState().token).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
  })

  it('login does not fail when localStorage cannot be written', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota')
    })
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'tok', token_type: 'bearer' })
    vi.mocked(authApi.fetchMe).mockResolvedValue(user)
    const store = await freshStore()
    await store.getState().login(user.email, 'secret123')
    expect(store.getState().token).toBe('tok')
  })

  it('register creates the account and then logs in', async () => {
    vi.mocked(authApi.register).mockResolvedValue(user)
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'tok', token_type: 'bearer' })
    vi.mocked(authApi.fetchMe).mockResolvedValue(user)
    const store = await freshStore()
    await store.getState().register(user.email, 'secret123', user.full_name)
    expect(authApi.register).toHaveBeenCalledWith(user.email, 'secret123', user.full_name)
    expect(store.getState().user).toEqual(user)
  })

  it('logout clears the token, the user and the persisted token', async () => {
    localStorage.setItem('auth_token', 'saved')
    const store = await freshStore()
    store.setState({ user })
    store.getState().logout()
    expect(store.getState().token).toBeNull()
    expect(store.getState().user).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
  })

  it('hydrate does nothing without a token', async () => {
    const store = await freshStore()
    await store.getState().hydrate()
    expect(authApi.fetchMe).not.toHaveBeenCalled()
  })

  it('hydrate loads the user of the persisted token', async () => {
    localStorage.setItem('auth_token', 'saved')
    vi.mocked(authApi.fetchMe).mockResolvedValue(user)
    const store = await freshStore()
    await store.getState().hydrate()
    expect(store.getState().user).toEqual(user)
  })

  it('hydrate logs out when the persisted token is rejected', async () => {
    localStorage.setItem('auth_token', 'stale')
    vi.mocked(authApi.fetchMe).mockRejectedValue(new Error('401'))
    const store = await freshStore()
    await store.getState().hydrate()
    expect(store.getState().token).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
  })
})
