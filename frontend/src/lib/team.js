import { apiRequest } from './auth'

export function getEventTeam(eventId) {
  return apiRequest(`/api/events/${eventId}/team/`)
}

export function getEventInvitations(eventId) {
  return apiRequest(`/api/events/${eventId}/invitations/`)
}

export function createEventInvitation(eventId, invitation) {
  return apiRequest(`/api/events/${eventId}/invitations/`, {
    method: 'POST',
    body: JSON.stringify(invitation),
  })
}

export function revokeEventInvitation(eventId, invitationId) {
  return apiRequest(
    `/api/events/${eventId}/invitations/${invitationId}/revoke/`,
    { method: 'POST' },
  )
}

export function acceptEventInvitation(token) {
  return apiRequest('/api/events/invitations/accept/', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}
