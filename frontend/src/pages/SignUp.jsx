import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CalendarDays, UserPlus } from 'lucide-react'
import { registerAccount } from '../lib/auth'
import { getPendingInvitation } from '../lib/invitationSession'

const initialForm = {
  first_name: '',
  last_name: '',
  username: '',
  email: '',
  password: '',
  confirm_password: '',
}

function errorMessage(error) {
  if (error.data) {
    const fieldError = Object.values(error.data).find(Array.isArray)
    if (fieldError?.length) return fieldError.join(' ')
  }
  return error.message || 'Unable to create your account.'
}

export default function SignUp() {
  const [form, setForm] = useState(initialForm)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [registered, setRegistered] = useState(false)

  const invited = Boolean(getPendingInvitation())

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setWorking(true)

    try {
      await registerAccount(form)
      setRegistered(true)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setWorking(false)
    }
  }

  return (
    <main className="min-h-screen bg-[#F7F9F5] px-5 py-12 text-[#1A3F22]">
      <div className="mx-auto w-full max-w-xl">
        <Link to="/" className="inline-flex items-center gap-2 text-xl font-bold">
          <CalendarDays size={25} className="text-[#58761B]" />
          tuviora<span className="text-[#D99201]">.</span>
        </Link>

        <section className="mt-9 rounded-3xl border border-[#E2E9DE] bg-white p-7 shadow-sm sm:p-10">
          <div className="grid h-16 w-16 place-items-center rounded-2xl bg-[#EDF3E8] text-[#58761B]">
            <UserPlus size={29} />
          </div>

          {registered ? (
            <>
              <h1 className="mt-7 text-3xl font-bold">Check your email</h1>
              <p className="mt-4 leading-7 text-[#647365]">
                We created your account and sent a verification link to
                {' '}<strong>{form.email}</strong>. Open the link to activate
                your account before signing in.
              </p>
              <div className="mt-6 rounded-xl bg-[#EDF3E8] p-4 text-sm text-[#31563A]">
                During local development, the verification email appears
                in the Django backend terminal.
              </div>
              {invited && (
                <p className="mt-5 text-sm text-[#647365]">
                  Your event invitation is saved in this browser tab.
                  After verification, return to your invitation to join the team.
                </p>
              )}
              <Link to="/operations"
                className="mt-7 inline-flex items-center gap-2 font-semibold text-[#58761B]">
                Go to sign in <ArrowRight size={17} />
              </Link>
            </>
          ) : (
            <>
              <p className="mt-7 text-sm font-semibold uppercase tracking-widest text-[#58761B]">
                {invited ? 'Join your event team' : 'Get started'}
              </p>
              <h1 className="mt-2 text-3xl font-bold">Create your account</h1>
              <p className="mt-3 text-[#647365]">
                {invited
                  ? 'Use the same email address that received your invitation.'
                  : 'Create an account to organize and collaborate on events.'}
              </p>

              <form onSubmit={handleSubmit} className="mt-8 space-y-5">
                <div className="grid gap-5 sm:grid-cols-2">
                  {[
                    ['first_name', 'First name'],
                    ['last_name', 'Last name'],
                  ].map(([field, label]) => (
                    <label key={field} className="block text-sm font-semibold">
                      {label}
                      <input
                        value={form[field]}
                        onChange={(event) => update(field, event.target.value)}
                        autoComplete={field === 'first_name' ? 'given-name' : 'family-name'}
                        required
                        maxLength={150}
                        className="mt-2 w-full rounded-xl border border-[#DCE5D8] px-4 py-3 outline-none focus:border-[#58761B]"
                      />
                    </label>
                  ))}
                </div>

                <label className="block text-sm font-semibold">
                  Username
                  <input
                    value={form.username}
                    onChange={(event) => update('username', event.target.value)}
                    autoComplete="username"
                    required
                    maxLength={150}
                    className="mt-2 w-full rounded-xl border border-[#DCE5D8] px-4 py-3 outline-none focus:border-[#58761B]"
                  />
                </label>

                <label className="block text-sm font-semibold">
                  Email address
                  <input
                    type="email"
                    value={form.email}
                    onChange={(event) => update('email', event.target.value)}
                    autoComplete="email"
                    required
                    className="mt-2 w-full rounded-xl border border-[#DCE5D8] px-4 py-3 outline-none focus:border-[#58761B]"
                  />
                </label>

                <div className="grid gap-5 sm:grid-cols-2">
                  {[
                    ['password', 'Password'],
                    ['confirm_password', 'Confirm password'],
                  ].map(([field, label]) => (
                    <label key={field} className="block text-sm font-semibold">
                      {label}
                      <input
                        type="password"
                        value={form[field]}
                        onChange={(event) => update(field, event.target.value)}
                        autoComplete={field === 'password' ? 'new-password' : 'new-password'}
                        required
                        minLength={8}
                        className="mt-2 w-full rounded-xl border border-[#DCE5D8] px-4 py-3 outline-none focus:border-[#58761B]"
                      />
                    </label>
                  ))}
                </div>

                {error && (
                  <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-800">
                    {error}
                  </p>
                )}

                <button type="submit" disabled={working}
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white hover:bg-[#31563A] disabled:opacity-50">
                  <UserPlus size={18} />
                  {working ? 'Creating account…' : 'Create account'}
                </button>
              </form>

              <p className="mt-6 text-center text-sm text-[#647365]">
                Already registered?{' '}
                <Link to="/operations" className="font-semibold text-[#58761B] hover:underline">
                  Sign in
                </Link>
              </p>
            </>
          )}
        </section>
      </div>
    </main>
  )
}
