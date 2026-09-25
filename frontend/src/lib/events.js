import { apiRequest } from './auth'

export function getEvents() {
  return apiRequest('/api/events/')
}

export function createEvent(event) {
  return apiRequest('/api/events/', {
    method: 'POST',
    body: JSON.stringify(event),
  })
}

function humanizeField(field) {
  if (field === 'non_field_errors' || field === 'detail') return ''
  return field.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
}

export function formatApiError(error) {
  if (error.status === 401 || error.status === 403) {
    return 'Your session has expired. Please sign in again.'
  }

  if (error.data && typeof error.data === 'object') {
    return Object.entries(error.data)
      .map(([field, messages]) => {
        const text = Array.isArray(messages)
          ? messages.join(', ')
          : String(messages)

        const label = humanizeField(field)
        return label ? `${label}: ${text}` : text
      })
      .join(' | ')
  }

  return error.message || 'Something went wrong.'
}

export function publishEvent(eventId) {
  return apiRequest(`/api/events/${eventId}/publish/`, {
    method: 'POST',
  })
}

export function getEventRegistrations(eventId) {
  return apiRequest(`/api/events/${eventId}/registrations/`)
}

export function registerForEvent(eventId, ticketTypeId) {
  return apiRequest(`/api/events/${eventId}/registrations/`, {
    method: 'POST',
    body: ticketTypeId
      ? JSON.stringify({ ticket_type_id: ticketTypeId })
      : undefined,
  })
}

export function getMyEventRegistration(eventId) {
  return apiRequest(`/api/events/${eventId}/registrations/me/`)
}

export function cancelMyEventRegistration(eventId) {
  return apiRequest(`/api/events/${eventId}/registrations/me/cancel/`, {
    method: 'POST',
  })
}


export function getMyRegistrations() {
  return apiRequest('/api/events/registrations/me/')
}

export function getEventTicketTypes(eventId) {
  return apiRequest(`/api/events/${eventId}/ticket-types/`)
}

export function createTicketType(eventId, ticketType) {
  return apiRequest(`/api/events/${eventId}/ticket-types/`, {
    method: 'POST',
    body: JSON.stringify(ticketType),
  })
}
