import { apiRequest } from './auth'

/**
 * Retrieve conference status and the current user's
 * conference management permissions.
 */
export function getConferenceStatus(eventId) {
  return apiRequest(
    `/api/voice/events/${eventId}/conference/`
  )
}

/**
 * Start an event conference.
 * Only the event organizer may perform this action.
 */
export function startConference(eventId) {
  return apiRequest(
    `/api/voice/events/${eventId}/conference/start/`,
    {
      method: 'POST',
    }
  )
}

/**
 * End an active event conference.
 * Only the event organizer may perform this action.
 */
export function endConference(eventId) {
  return apiRequest(
    `/api/voice/events/${eventId}/conference/end/`,
    {
      method: 'POST',
    }
  )
}

/**
 * Request a short-lived conference access code.
 * Available only to authorized event team members.
 */
export function generateConferenceAccessCode(eventId) {
  return apiRequest(
    `/api/voice/events/${eventId}/conference/access-code/`,
    {
      method: 'POST',
    }
  )
}
