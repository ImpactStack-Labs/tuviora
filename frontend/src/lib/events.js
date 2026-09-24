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

        return `${field}: ${text}`
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
