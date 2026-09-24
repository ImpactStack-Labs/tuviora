import { apiRequest } from './auth'

export function getReadinessTasks(eventId) {
  return apiRequest(`/api/events/${eventId}/tasks/`)
}

export function createReadinessTask(eventId, task) {
  return apiRequest(`/api/events/${eventId}/tasks/`, {
    method: 'POST',
    body: JSON.stringify(task),
  })
}

export function updateReadinessTask(eventId, taskId, changes) {
  return apiRequest(`/api/events/${eventId}/tasks/${taskId}/`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}
