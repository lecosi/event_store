import { apiClient } from './client'
import type { Page, Participant, ParticipantFilters, ParticipantListParams } from '../types'

const DEFAULT_FILE_NAME = 'participantes.csv'

/** One page of the participants report. */
export async function listParticipants(
  params: ParticipantListParams = {},
): Promise<Page<Participant>> {
  const { data } = await apiClient.get<Page<Participant>>('/reports/participants', { params })
  return data
}

/** The file name from `Content-Disposition`; a plain name or the default when it is missing or unsafe. */
function fileNameOf(header: unknown): string {
  const name = /filename="?([^";]+)"?/.exec(String(header ?? ''))?.[1]
  return name && !/[\\/]/.test(name) ? name : DEFAULT_FILE_NAME
}

/** Downloads the participants matching `filters` as a CSV file through the browser. */
export async function downloadParticipantsCsv(filters: ParticipantFilters = {}): Promise<void> {
  const { data, headers } = await apiClient.get<Blob>('/reports/participants.csv', {
    params: filters,
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = fileNameOf(headers['content-disposition'])
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
