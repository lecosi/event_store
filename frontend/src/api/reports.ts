import { apiClient } from './client'
import type {
  Page,
  Participant,
  ParticipantFilters,
  ParticipantListParams,
  SessionParticipant,
  SessionParticipantFilters,
  SessionParticipantListParams,
} from '../types'

const DEFAULT_FILE_NAME = 'participantes.csv'
const DEFAULT_SESSION_FILE_NAME = 'participantes_sesiones.csv'

/** One page of the participants report. */
export async function listParticipants(
  params: ParticipantListParams = {},
): Promise<Page<Participant>> {
  const { data } = await apiClient.get<Page<Participant>>('/reports/participants', { params })
  return data
}

/** One page of the session participants report. */
export async function listSessionParticipants(
  params: SessionParticipantListParams = {},
): Promise<Page<SessionParticipant>> {
  const { data } = await apiClient.get<Page<SessionParticipant>>('/reports/sessions/participants', {
    params,
  })
  return data
}

/** The file name from `Content-Disposition`; a plain name or the default when it is missing or unsafe. */
function fileNameOf(header: unknown, defaultName: string): string {
  const name = /filename="?([^";]+)"?/.exec(String(header ?? ''))?.[1]
  return name && !/[\\/]/.test(name) ? name : defaultName
}

async function downloadCsv(
  path: string,
  filters: ParticipantFilters | SessionParticipantFilters,
  defaultName: string,
): Promise<void> {
  const { data, headers } = await apiClient.get<Blob>(path, {
    params: filters,
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = fileNameOf(headers['content-disposition'], defaultName)
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

/** Downloads the participants matching `filters` as a CSV file through the browser. */
export function downloadParticipantsCsv(filters: ParticipantFilters = {}): Promise<void> {
  return downloadCsv('/reports/participants.csv', filters, DEFAULT_FILE_NAME)
}

/** Downloads the session participants matching `filters` as a CSV file through the browser. */
export function downloadSessionParticipantsCsv(
  filters: SessionParticipantFilters = {},
): Promise<void> {
  return downloadCsv('/reports/sessions/participants.csv', filters, DEFAULT_SESSION_FILE_NAME)
}
