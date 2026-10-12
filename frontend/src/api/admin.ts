import { apiClient } from './client'
import type { Page, User, UserListParams, UserUpdatePayload } from '../types'

/** Admin only: one page of user accounts, optionally those whose email starts with `email`. */
export async function listUsers(params: UserListParams = {}): Promise<Page<User>> {
  const { data } = await apiClient.get<Page<User>>('/admin/users', { params })
  return data
}

/** Admin only: `payload` holds just the fields that changed. */
export async function updateUser(id: number, payload: UserUpdatePayload): Promise<User> {
  const { data } = await apiClient.patch<User>(`/admin/users/${id}`, payload)
  return data
}
