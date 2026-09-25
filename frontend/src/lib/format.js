// Event date/time are stored as plain "YYYY-MM-DD" / "HH:MM" strings with no
// timezone — parsed and formatted as UTC noon so the calendar date shown never
// shifts with the viewer's local timezone.
export function formatEventDate(value) {
  if (!value) return 'Date not set'

  const date = new Date(`${value}T12:00:00Z`)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('en-UG', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date)
}

export function formatEventTime(value) {
  if (!value) return 'Not set'

  const [hoursRaw, minutesRaw] = value.split(':')
  const hours = Number(hoursRaw)
  const minutes = Number(minutesRaw)

  if (
    !Number.isInteger(hours) ||
    !Number.isInteger(minutes) ||
    hours < 0 ||
    hours > 23 ||
    minutes < 0 ||
    minutes > 59
  ) {
    return value
  }

  const period = hours >= 12 ? 'PM' : 'AM'
  const hour = hours % 12 || 12

  return `${hour}:${String(minutes).padStart(2, '0')} ${period}`
}

// For real timestamps (e.g. invitation.expires_at) — shown in the viewer's
// own local time, unlike formatEventDate.
export function formatDateTime(value) {
  if (!value) return 'Not set'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat('en-UG', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date)
}
