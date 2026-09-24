import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, CalendarDays, LockKeyhole, LogIn } from 'lucide-react'
import { loginOrganizer } from '../lib/auth'
import { safeAttendeePath } from '../lib/attendeeReturn'

function safeNextPath(value) {
  return safeAttendeePath(value) || '/events'
}

export default function AttendeeLogin() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const nextPath = safeNextPath(params.get('next'))

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      await loginOrganizer(username, password)
      navigate(nextPath, { replace: true })
    } catch (err) {
      setError(err.message || 'Unable to sign in.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F7F9F5] px-5 py-12 text-[#1A3F22]">
      <div className="w-full max-w-md rounded-3xl border border-[#E3E9DF] bg-white p-8 shadow-sm sm:p-10">
        <Link to="/events" className="inline-flex items-center gap-2 text-sm font-semibold text-[#58761B]">
          <ArrowLeft size={17} />
          Back to events
        </Link>

        <div className="mt-8 grid h-16 w-16 place-items-center rounded-2xl bg-[#EDF3E8] text-[#58761B]">
          <CalendarDays size={30} />
        </div>

        <p className="mt-7 text-sm font-semibold uppercase tracking-widest text-[#58761B]">
          Tuviora events
        </p>
        <h1 className="mt-2 text-3xl font-bold">Attendee sign in</h1>
        <p className="mt-3 leading-7 text-[#647064]">
          Sign in to register for events and manage your registrations.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <label className="block text-sm font-semibold">
            Username
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
              className="mt-2 w-full rounded-xl border border-[#DCE5D8] px-4 py-3 outline-none focus:border-[#58761B]"
            />
          </label>

          <label className="block text-sm font-semibold">
            Password
            <div className="relative mt-2">
              <LockKeyhole
                size={19}
                className="absolute left-4 top-3.5 text-[#718072]"
              />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
                className="w-full rounded-xl border border-[#DCE5D8] py-3 pl-12 pr-4 outline-none focus:border-[#58761B]"
              />
            </div>
          </label>

          {error && (
            <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3 font-semibold text-white transition hover:bg-[#31563A] disabled:opacity-60"
          >
            <LogIn size={19} />
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="mt-7 text-center text-sm text-[#647064]">
          New to Tuviora?{' '}
          <Link
            to={`/signup?next=${encodeURIComponent(nextPath)}`}
            className="font-semibold text-[#58761B] hover:underline"
          >
            Create an account
          </Link>
        </p>
      </div>
    </main>
  )
}
