import { apiClient } from './client'
import type { Session, SessionPayload } from '../types'

export async function createSession(eventId: number, payload: SessionPayload): Promise<Session> {
  const { data } = await apiClient.post<Session>(`/events/${eventId}/sessions`, payload)
  return data
}

export async function updateSession(
  eventId: number,
  sessionId: number,
  payload: SessionPayload,
): Promise<Session> {
  const { data } = await apiClient.put<Session>(`/events/${eventId}/sessions/${sessionId}`, payload)
  return data
}

export async function deleteSession(eventId: number, sessionId: number): Promise<void> {
  await apiClient.delete(`/events/${eventId}/sessions/${sessionId}`)
}
