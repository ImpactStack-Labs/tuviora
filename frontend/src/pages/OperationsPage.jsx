import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import OrganizerLayout from '../layouts/OrganizerLayout'
import OrganizerLogin from './OrganizerLogin'
import TeamWorkspace from './TeamWorkspace'
import { getCurrentUser, logoutOrganizer } from '../lib/auth'

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

  if (!user.is_organizer) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#F7F9F5] px-5">
        <div className="w-full max-w-lg rounded-2xl border border-[#E3E9DF] bg-white p-8 text-center shadow-sm">
          <h1 className="text-2xl font-bold text-[#1A3F22]">
            Organizer access required
          </h1>

          <p className="mt-4 text-[#647064]">
            You're signed in as {user.username}. This account
            doesn't have access to the organizer workspace.
          </p>

          <p className="mt-2 text-sm text-[#647064]">
            You can continue browsing events or sign out
            and use a different account.
          </p>

          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Link
              to="/events"
              className="rounded-lg bg-[#1A3F22] px-5 py-3 font-semibold text-white"
            >
              Browse events
            </Link>

            <button
              type="button"
              onClick={async () => {
                try {
                  await logoutOrganizer()
                  setUser(null)
                } catch (err) {
                  setError(err.message || 'Unable to sign out.')
                }
              }}
              className="rounded-lg border border-[#DDE6D6] px-5 py-3 font-semibold text-[#1A3F22]"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <OrganizerLayout
      user={user}
      onLogout={() => setUser(null)}
    />
  )
}
