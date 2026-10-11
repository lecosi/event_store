import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest'
import { apiClient } from './client'
import { downloadParticipantsCsv, listParticipants } from './reports'

let sent: InternalAxiosRequestConfig | undefined
let click: MockInstance<() => void>
const createObjectURL = vi.fn(() => 'blob:report')
const revokeObjectURL = vi.fn()

function answerWith(status: number, data: unknown, headers: Record<string, string> = {}) {
  apiClient.defaults.adapter = async (config) => {
    sent = config
    const response = { status, data, statusText: '', headers, config }
    if (status >= 400) throw new AxiosError('failed', 'ERR_BAD_REQUEST', config, null, response)
    return response
  }
}

const clicked = () => click.mock.contexts[0] as HTMLAnchorElement
const csvBlob = () => new Blob(['a;b'], { type: 'text/csv' })

beforeEach(() => {
  sent = undefined
  createObjectURL.mockClear()
  revokeObjectURL.mockClear()
  URL.createObjectURL = createObjectURL
  URL.revokeObjectURL = revokeObjectURL
  click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('listParticipants', () => {
  it('gets /reports/participants with the filters and the pagination', async () => {
    answerWith(200, { items: [], total: 0, page: 2, size: 10, pages: 0 })
    const page = await listParticipants({ q: 'pycon', status: 'published', page: 2, size: 10 })
    expect(sent?.method).toBe('get')
    expect(sent?.url).toBe('/reports/participants')
    expect(sent?.params).toEqual({ q: 'pycon', status: 'published', page: 2, size: 10 })
    expect(page.page).toBe(2)
  })
})

describe('downloadParticipantsCsv', () => {
  it('requests the csv as a blob with the same filters and no pagination', async () => {
    answerWith(200, csvBlob())
    await downloadParticipantsCsv({ event_id: 5, date_from: '2030-01-01' })
    expect(sent?.url).toBe('/reports/participants.csv')
    expect(sent?.responseType).toBe('blob')
    expect(sent?.params).toEqual({ event_id: 5, date_from: '2030-01-01' })
  })

  it('downloads the file through a temporary link named by the server', async () => {
    answerWith(200, csvBlob(), {
      'content-disposition': 'attachment; filename="participantes_20301231.csv"',
    })
    await downloadParticipantsCsv({})
    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(clicked().href).toBe('blob:report')
    expect(clicked().download).toBe('participantes_20301231.csv')
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:report')
    expect(document.body.querySelector('a')).toBeNull()
  })

  it('falls back to a default file name when the header is not readable', async () => {
    answerWith(200, csvBlob())
    await downloadParticipantsCsv({})
    expect(clicked().download).toBe('participantes.csv')
  })

  it.each([
    ['a header without a file name', 'attachment'],
    ['a file name with a path', 'attachment; filename="../etc/passwd"'],
  ])('uses the default file name for %s', async (_label, header) => {
    answerWith(200, csvBlob(), { 'content-disposition': header })
    await downloadParticipantsCsv({})
    expect(clicked().download).toBe('participantes.csv')
  })

  it('rejects with the translated message when the error body is a blob', async () => {
    const body = new Blob([JSON.stringify({ detail: 'date_to must not be before date_from' })], {
      type: 'application/json',
    })
    answerWith(422, body)
    await expect(downloadParticipantsCsv({})).rejects.toMatchObject({
      message: 'La fecha final no puede ser anterior a la fecha inicial.',
      status: 422,
    })
    expect(createObjectURL).not.toHaveBeenCalled()
  })

  it('keeps the generic message when the blob error body is not json', async () => {
    answerWith(500, new Blob(['boom']))
    await expect(downloadParticipantsCsv({})).rejects.toMatchObject({
      message: 'Algo salió mal. Inténtalo de nuevo.',
      status: 500,
    })
  })
})
