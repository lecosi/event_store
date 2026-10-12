import { apiClient } from './client'
import type { Page, RegisteredEvent, Registration, SessionRegistration } from '../types'

export async function register(eventId: number): Promise<Registration> {
  const { data } = await apiClient.post<Registration>(`/events/${eventId}/register`)
  return data
}

export async function unregister(eventId: number): Promise<void> {
  await apiClient.delete(`/events/${eventId}/register`)
}

export async function enrollInSession(
  eventId: number,
  sessionId: number,
): Promise<SessionRegistration> {
  const { data } = await apiClient.post<SessionRegistration>(
    `/events/${eventId}/sessions/${sessionId}/register`,
  )
  return data
}

export async function cancelSessionEnrollment(eventId: number, sessionId: number): Promise<void> {
  await apiClient.delete(`/events/${eventId}/sessions/${sessionId}/register`)
}

/** Events the logged-in user is registered to, newest registrations included. */
export async function listMyEvents(page = 1, size = 10): Promise<Page<RegisteredEvent>> {
  const { data } = await apiClient.get<Page<RegisteredEvent>>('/users/me/events', {
    params: { page, size },
  })
  return data
}
