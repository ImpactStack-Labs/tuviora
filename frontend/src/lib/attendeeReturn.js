const RETURN_KEY = 'tuviora.attendeeReturnPath'

export function safeAttendeePath(value) {
  if (
    typeof value === 'string' &&
    /^\/events(?:\/\d+)?\/?$/.test(value)
  ) {
    return value
  }

  return ''
}

export function saveAttendeeReturn(value) {
  const path = safeAttendeePath(value)

  if (path) {
    sessionStorage.setItem(RETURN_KEY, path)
  }

  return path
}

export function getAttendeeReturn() {
  return safeAttendeePath(sessionStorage.getItem(RETURN_KEY))
}

export function clearAttendeeReturn() {
  sessionStorage.removeItem(RETURN_KEY)
}
