const KEY = 'tuviora.pendingInvitation'

export function savePendingInvitation(token) {
  if (token) sessionStorage.setItem(KEY, token)
}

export function getPendingInvitation() {
  return sessionStorage.getItem(KEY) || ''
}

export function clearPendingInvitation() {
  sessionStorage.removeItem(KEY)
}

export function invitationPath() {
  const token = getPendingInvitation()
  return token ? `/invite#token=${encodeURIComponent(token)}` : '/operations'
}
