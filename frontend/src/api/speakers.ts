import { apiClient } from './client'
import type { Page, Speaker, SpeakerListParams, SpeakerPayload } from '../types'

/** Speakers ordered by name; `q` is a case-insensitive substring of the name. */
export async function listSpeakers(params: SpeakerListParams = {}): Promise<Page<Speaker>> {
  const { data } = await apiClient.get<Page<Speaker>>('/speakers', { params })
  return data
}

export async function createSpeaker(payload: SpeakerPayload): Promise<Speaker> {
  const { data } = await apiClient.post<Speaker>('/speakers', payload)
  return data
}
