import { apiRequest } from './auth'

export function getEventSummary(eventId) {
  return apiRequest(`/api/events/${eventId}/summary/`)
}

export function getEventPayments(eventId) {
  return apiRequest(`/api/events/${eventId}/payments/`)
}

export function getBudgetItems(eventId) {
  return apiRequest(`/api/events/${eventId}/budget/`)
}

export function createBudgetItem(eventId, item) {
  return apiRequest(`/api/events/${eventId}/budget/`, {
    method: 'POST',
    body: JSON.stringify(item),
  })
}

export function updateBudgetItem(eventId, itemId, changes) {
  return apiRequest(`/api/events/${eventId}/budget/${itemId}/`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function deleteBudgetItem(eventId, itemId) {
  return apiRequest(`/api/events/${eventId}/budget/${itemId}/`, {
    method: 'DELETE',
  })
}

export function formatMoney(value, currency) {
  const amount = Number(value || 0).toLocaleString(undefined, {
    maximumFractionDigits: 0,
  })
  return `${currency} ${amount}`
}
