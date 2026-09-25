import { apiRequest } from './auth'

export function getAnnouncements(eventId) {
  return apiRequest(`/api/events/${eventId}/announcements/`)
}

export function sendAnnouncement(eventId, message) {
  return apiRequest(`/api/events/${eventId}/announcements/`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}
