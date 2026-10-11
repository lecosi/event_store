// TypeScript mirrors of the FastAPI response/request schemas
// (backend/app/api/schemas.py, event_schemas.py, speaker_schemas.py).
// Datetimes travel as ISO-8601 strings.

export type Role = 'admin' | 'organizer' | 'attendee'
export type EventStatus = 'draft' | 'published' | 'cancelled' | 'finished'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface Event {
  id: number
  name: string
  description: string
  location: string
  start_at: string
  end_at: string
  capacity: number
  status: EventStatus
  organizer_id: number
}

export interface SpeakerRef {
  id: number
  name: string
}

export interface Session {
  id: number
  event_id: number
  title: string
  start_at: string
  end_at: string
  capacity: number
  speaker: SpeakerRef
}

/** GET /events/{id}: the event plus sessions and registration info for the viewer. */
export interface EventDetail extends Event {
  sessions: Session[]
  registered_count: number
  available_spots: number
  is_registered: boolean
}

/** Body of POST /events and PUT /events/{id}. */
export interface EventPayload {
  name: string
  description: string
  location: string
  start_at: string
  end_at: string
  capacity: number
}

/** Generic paginated envelope used by every list endpoint. */
export interface Page<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface EventListParams {
  q?: string
  status?: EventStatus
  page?: number
  size?: number
}

export interface Registration {
  user_id: number
  event_id: number
  created_at: string
}

export interface RegisteredEvent extends Event {
  registered_at: string
}

export interface Speaker {
  id: number
  name: string
  bio: string
  email: string | null
}

/** Query of GET /speakers: `q` searches the name. */
export interface SpeakerListParams {
  q?: string
  page?: number
  size?: number
}

/** Body of POST /speakers; `email` is omitted when blank. */
export interface SpeakerPayload {
  name: string
  bio: string
  email?: string
}

/** Body of POST /events/{id}/sessions and PUT /events/{id}/sessions/{sid}. */
export interface SessionPayload {
  title: string
  speaker_id: number
  start_at: string
  end_at: string
  capacity: number
}
