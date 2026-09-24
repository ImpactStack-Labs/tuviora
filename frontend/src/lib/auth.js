function getCookie(name) {
  const value = document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith(`${name}=`))

  return value
    ? decodeURIComponent(value.split('=').slice(1).join('='))
    : ''
}

export async function apiRequest(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    await fetch('/api/auth/csrf/', {
      credentials: 'same-origin',
    })
  }

  const headers = new Headers(options.headers || {})

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers.set('X-CSRFToken', getCookie('csrftoken'))
  }

  const response = await fetch(path, {
    ...options,
    headers,
    credentials: 'same-origin',
  })

  let data = null

  try {
    data = await response.json()
  } catch {
    // Some endpoints may return an empty response.
  }

  if (!response.ok) {
    const error = new Error(
      data?.detail ||
      `Request failed with HTTP ${response.status}`
    )

    error.status = response.status
    error.data = data
    throw error
  }

  return data
}

export function getCurrentUser() {
  return apiRequest('/api/auth/me/')
}

export function loginOrganizer(username, password) {
  return apiRequest('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function logoutOrganizer() {
  return apiRequest('/api/auth/logout/', {
    method: 'POST',
  })
}


export function registerAccount(payload) {
  return apiRequest('/api/auth/register/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function verifyEmail(token) {
  return apiRequest('/api/auth/verify-email/', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}
