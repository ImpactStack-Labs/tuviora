import { apiRequest } from './auth'

export function getEventFeedback(eventId) {
  return apiRequest(`/api/events/${eventId}/feedback/`)
}

export function getMyFeedback(eventId) {
  return apiRequest(`/api/events/${eventId}/feedback/me/`)
}

export function submitFeedback(eventId, { rating, comment }) {
  return apiRequest(`/api/events/${eventId}/feedback/`, {
    method: 'POST',
    body: JSON.stringify({ rating, comment }),
  })
}

export function getFeedbackAnalysis(eventId) {
  return apiRequest(`/api/events/${eventId}/feedback/analysis/`)
}

export function generateFeedbackAnalysis(eventId) {
  return apiRequest(`/api/events/${eventId}/feedback/analysis/`, {
    method: 'POST',
  })
}
