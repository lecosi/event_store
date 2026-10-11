import { create } from 'zustand'
import * as authApi from '../api/auth'
import type { User } from '../types'

export const TOKEN_STORAGE_KEY = 'auth_token'

/** localStorage can throw (private mode, blocked storage); never let that break the app. */
function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token)
    else localStorage.removeItem(TOKEN_STORAGE_KEY)
  } catch {
    // Ignore: the session just will not survive a reload.
  }
}

interface AuthState {
  token: string | null
  user: User | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
  /** Fetches the profile of the current token. */
  loadMe: () => Promise<void>
  /** Call once on app start: restores the user from a persisted token. */
  hydrate: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: readToken(),
  user: null,

  login: async (email, password) => {
    const { access_token } = await authApi.login(email, password)
    // Token goes in first so the request interceptor can authenticate /users/me.
    writeToken(access_token)
    set({ token: access_token })
    try {
      await get().loadMe()
    } catch (error) {
      get().logout()
      throw error
    }
  },

  // The API returns the created user but no token, so log in right after.
  register: async (email, password) => {
    await authApi.register(email, password)
    await get().login(email, password)
  },

  logout: () => {
    writeToken(null)
    set({ token: null, user: null })
  },

  loadMe: async () => {
    set({ user: await authApi.fetchMe() })
  },

  hydrate: async () => {
    if (!get().token) return
    try {
      await get().loadMe()
    } catch {
      get().logout()
    }
  },
}))
