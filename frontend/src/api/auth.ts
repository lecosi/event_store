import { apiClient } from './client'
import type { TokenResponse, User } from '../types'

export async function register(email: string, password: string, fullName: string): Promise<User> {
  const { data } = await apiClient.post<User>('/auth/register', {
    email,
    password,
    full_name: fullName,
  })
  return data
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', { email, password })
  return data
}

/** Profile of the user owning the current token. */
export async function fetchMe(): Promise<User> {
  const { data } = await apiClient.get<User>('/users/me')
  return data
}
