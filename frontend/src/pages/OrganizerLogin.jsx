import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarDays, LockKeyhole, LogIn } from 'lucide-react'
import { getCurrentUser, loginOrganizer } from '../lib/auth'

export default function OrganizerLogin({ onLogin }) {
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
      const result = await getCurrentUser()
      onLogin(result.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F7F9F5] px-5 py-12">
      <div className="w-full max-w-md rounded-3xl border border-[#E3E9DF] bg-white p-8 shadow-sm sm:p-10">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[#EDF3E8] text-[#58761B]">
          <CalendarDays size={30} />
        </div>

        <div className="mt-7 text-center">
          <p className="font-semibold text-[#58761B]">
            Tuviora
          </p>
          <h1 className="mt-2 text-3xl font-bold text-[#1A3F22]">
            Organizer sign in
          </h1>
          <p className="mt-3 text-[#647064]">
            Sign in to manage your events, preparations and communications.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <div>
            <label htmlFor="username" className="font-semibold text-[#1A3F22]">
              Username
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
              className="mt-2 w-full rounded-xl border border-[#DCE5D8] px-4 py-3 outline-none focus:border-[#58761B]"
            />
          </div>

          <div>
            <label htmlFor="password" className="font-semibold text-[#1A3F22]">
              Password
            </label>
            <div className="relative mt-2">
              <LockKeyhole
                size={19}
                className="absolute left-4 top-3.5 text-[#718072]"
              />
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                className="w-full rounded-xl border border-[#DCE5D8] py-3 pl-12 pr-4 outline-none focus:border-[#58761B]"
              />
            </div>
          </div>

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
        <p className="mt-6 text-center text-sm text-[#647064]">
          New to Tuviora?{' '}
          <Link to="/signup" className="font-semibold text-[#58761B] hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}
