import { useEffect, useState } from 'react'
import OrganizerLayout from '../layouts/OrganizerLayout'
import OrganizerLogin from './OrganizerLogin'
import TeamWorkspace from './TeamWorkspace'
import { getCurrentUser } from '../lib/auth'

export default function OperationsPage() {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    getCurrentUser()
      .then((result) => {
        if (active) setUser(result.user)
      })
      .catch((err) => {
        if (active && err.status !== 401 && err.status !== 403) {
          setError(err.message)
        }
      })
      .finally(() => {
        if (active) setChecking(false)
      })

    return () => {
      active = false
    }
  }, [])

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F7F9F5] text-[#1A3F22]">
        Checking your session...
      </div>
    )
  }

  if (error) {
    return (
      <div role="alert" className="mx-auto max-w-lg p-8 text-red-700">
        Unable to connect to the authentication service: {error}
      </div>
    )
  }

  if (!user) {
    return (
      <OrganizerLogin
        onLogin={(loggedInUser) => {
          setUser(loggedInUser)
        }}
      />
    )
  }

  if (!user.is_organizer && user.team_memberships?.length) {
    return (
      <TeamWorkspace
        user={user}
        onLogout={() => setUser(null)}
      />
    )
  }

  return <OrganizerLayout />
}
