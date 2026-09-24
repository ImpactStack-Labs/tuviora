import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  clearPendingInvitation,
  getPendingInvitation,
  savePendingInvitation,
} from '../lib/invitationSession'
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  LockKeyhole,
  LogIn,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { getCurrentUser, loginOrganizer } from '../lib/auth'
import { acceptEventInvitation } from '../lib/team'
import { formatApiError } from '../lib/events'

const ROLE_LABELS = {
  manager: 'Event Manager',
  member: 'Team Member',
}

function readInvitationToken() {
  const fragment = new URLSearchParams(
    window.location.hash.replace(/^#/, ''),
  )

  // Also support invitation links generated before this page existed.
  const query = new URLSearchParams(window.location.search)
  const token = fragment.get('token') || query.get('token') || ''

  // Remove the credential from the visible URL and browser history.
  if (token) {
    window.history.replaceState(
      window.history.state,
      '',
      window.location.pathname,
    )
  }

  if (token) savePendingInvitation(token)
  return token || getPendingInvitation()
}

export default function AcceptInvitation() {
  const [token] = useState(readInvitationToken)
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [accepted, setAccepted] = useState(null)

  useEffect(() => {
    let active = true

    getCurrentUser()
      .then((result) => {
        if (active) setUser(result.user)
      })
      .catch((err) => {
        if (active && err.status !== 401 && err.status !== 403) {
          setError(formatApiError(err))
        }
      })
      .finally(() => {
        if (active) setChecking(false)
      })

    return () => { active = false }
  }, [])

  async function handleSignIn(event) {
    event.preventDefault()
    if (working) return

    setWorking(true)
    setError('')

    try {
      const result = await loginOrganizer(username, password)
      setUser(result.user)
      setPassword('')
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setWorking(false)
    }
  }

  async function handleAccept() {
    if (!token || working) return

    setWorking(true)
    setError('')

    try {
      const result = await acceptEventInvitation(token)
      setAccepted(result)
      clearPendingInvitation()
    } catch (err) {
      setError(err.data?.detail || err.message || 'Unable to accept invitation.')
    } finally {
      setWorking(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F7F9F5] px-5 py-12 text-[#1A3F22]">
      <div className="mx-auto max-w-lg">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xl font-bold"
        >
          <CalendarDays size={25} className="text-[#58761B]" />
          tuviora<span className="text-[#D99201]">.</span>
        </Link>

        <div className="mt-10 rounded-3xl border border-[#E2E9DE] bg-white p-7 shadow-sm sm:p-10">
          <div className="grid h-16 w-16 place-items-center rounded-2xl bg-[#EDF3E8] text-[#58761B]">
            {accepted ? <CheckCircle2 size={30} /> : <Users size={30} />}
          </div>

          <p className="mt-7 text-sm font-semibold uppercase tracking-[0.15em] text-[#58761B]">
            Event collaboration
          </p>

          {accepted ? (
            <>
              <h1 className="mt-2 text-3xl font-bold">
                Welcome to the team!
              </h1>
              <p className="mt-4 text-[#647365]">
                You've successfully joined the event.
              </p>

              <div className="mt-7 rounded-2xl bg-[#F7F9F5] p-5">
                <p className="text-sm text-[#647365]">Your event</p>
                <p className="mt-1 text-xl font-bold">
                  {accepted.event_name}
                </p>
                <p className="mt-4 text-sm text-[#647365]">Your role</p>
                <p className="mt-1 font-semibold text-[#58761B]">
                  {ROLE_LABELS[accepted.role] || accepted.role}
                </p>
              </div>

              <p className="mt-5 text-sm text-[#647365]">
                Your organizer can now see you in the event team.
                Your task workspace will be available once task
                assignment is connected.
              </p>

              <Link
                to="/"
                className="mt-7 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white"
              >
                Back to Tuviora <ArrowRight size={18} />
              </Link>
            </>
          ) : (
            <>
              <h1 className="mt-2 text-3xl font-bold">
                Join your event team
              </h1>
              <p className="mt-3 text-[#647365]">
                Sign in with the account matching your invitation,
                then accept your event role.
              </p>

              {!token && (
                <div role="alert" className="mt-6 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
                  This invitation link is missing its token.
                  Ask your organizer for a new link.
                </div>
              )}

              {error && (
                <div role="alert" className="mt-6 rounded-xl bg-red-50 p-4 text-sm text-red-800">
                  {error}
                </div>
              )}

              {checking ? (
                <p className="mt-7 text-sm text-[#647365]">
                  Checking your session…
                </p>
              ) : !user ? (
                <form onSubmit={handleSignIn} className="mt-7 space-y-5">
                  <div>
                    <label htmlFor="invite-username" className="block text-sm font-semibold">
                      Username
                    </label>
                    <input
                      id="invite-username"
                      autoComplete="username"
                      required
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      className="mt-2 w-full rounded-xl border border-[#DCE5D8] px-4 py-3 outline-none focus:border-[#58761B]"
                    />
                  </div>

                  <div>
                    <label htmlFor="invite-password" className="block text-sm font-semibold">
                      Password
                    </label>
                    <div className="relative mt-2">
                      <LockKeyhole
                        size={18}
                        className="absolute left-4 top-3.5 text-[#718072]"
                      />
                      <input
                        id="invite-password"
                        type="password"
                        autoComplete="current-password"
                        required
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        className="w-full rounded-xl border border-[#DCE5D8] py-3 pl-12 pr-4 outline-none focus:border-[#58761B]"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={!token || working}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white disabled:opacity-50"
                  >
                    <LogIn size={18} />
                    {working ? 'Signing in…' : 'Sign in'}
                  </button>
                  <p className="text-center text-sm text-[#647365]">
                    Don't have an account?{' '}
                    <Link to="/signup" className="font-semibold text-[#58761B] hover:underline">
                      Create account
                    </Link>
                  </p>
                </form>
              ) : (
                <div className="mt-7 space-y-5">
                  <div className="rounded-xl border border-[#DCE5D8] bg-[#F7F9F5] p-4">
                    <div className="flex items-center gap-3">
                      <ShieldCheck size={23} className="text-[#58761B]" />
                      <div>
                        <p className="text-sm text-[#647365]">
                          Signed in as
                        </p>
                        <p className="font-semibold">{user.username}</p>
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleAccept}
                    disabled={!token || working}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white disabled:opacity-50"
                  >
                    <CheckCircle2 size={19} />
                    {working ? 'Joining event…' : 'Accept invitation'}
                  </button>

                  <p className="text-center text-xs text-[#647365]">
                    Signed in with the wrong account?
                    Open the organizer workspace to sign out,
                    then return using your invitation link.
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
