import { apiClient } from './client'
import type { Event, EventDetail, EventListParams, EventPayload, EventStatus, Page } from '../types'

export async function listEvents(params: EventListParams = {}): Promise<Page<Event>> {
  const { data } = await apiClient.get<Page<Event>>('/events', { params })
  return data
}

/** The event with its sessions and the availability for the current viewer. */
export async function getEvent(id: number): Promise<EventDetail> {
  const { data } = await apiClient.get<EventDetail>(`/events/${id}`)
  return data
}

export async function createEvent(payload: EventPayload): Promise<EventDetail> {
  const { data } = await apiClient.post<EventDetail>('/events', payload)
  return data
}

export async function updateEvent(id: number, payload: EventPayload): Promise<EventDetail> {
  const { data } = await apiClient.put<EventDetail>(`/events/${id}`, payload)
  return data
}

export async function updateStatus(id: number, status: EventStatus): Promise<EventDetail> {
  const { data } = await apiClient.patch<EventDetail>(`/events/${id}/status`, { status })
  return data
}

export async function deleteEvent(id: number): Promise<void> {
  await apiClient.delete(`/events/${id}`)
}
