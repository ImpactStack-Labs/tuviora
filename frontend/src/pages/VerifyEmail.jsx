import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarDays, CheckCircle2, MailCheck } from 'lucide-react'
import { verifyEmail } from '../lib/auth'
import { invitationPath } from '../lib/invitationSession'

const TOKEN_KEY = 'tuviora.emailVerificationToken'

function readToken() {
  const fragment = new URLSearchParams(
    window.location.hash.replace(/^#/, ''),
  )

  const token = fragment.get('token')

  if (token) {
    // Preserve the token across React development remounts.
    sessionStorage.setItem(TOKEN_KEY, token)

    // Remove the token from the visible URL.
    window.history.replaceState(
      window.history.state,
      '',
      window.location.pathname,
    )

    return token
  }

  return sessionStorage.getItem(TOKEN_KEY) || ''
}

export default function VerifyEmail() {
  const [token] = useState(readToken)
  const [status, setStatus] = useState(
    token ? 'ready' : 'missing',
  )
  const [error, setError] = useState('')

  async function handleVerify() {
    if (!token || status !== 'ready') return

    setStatus('working')
    setError('')

    try {
      await verifyEmail(token)
      sessionStorage.removeItem(TOKEN_KEY)
      setStatus('verified')
    } catch (err) {
      setError(
        err.data?.detail ||
        err.message ||
        'Email verification failed.',
      )
      setStatus('error')
    }
  }

  const nextPath = invitationPath()

  return (
    <main className="min-h-screen bg-[#F7F9F5] px-5 py-12 text-[#1A3F22]">
      <div className="mx-auto max-w-lg">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xl font-bold"
        >
          <CalendarDays size={25} className="text-[#58761B]" />
          tuviora<span className="text-[#D99201]">.</span>
        </Link>

        <section className="mt-10 rounded-3xl border border-[#E2E9DE] bg-white p-8 shadow-sm sm:p-10">
          <div className="grid h-16 w-16 place-items-center rounded-2xl bg-[#EDF3E8] text-[#58761B]">
            {status === 'verified'
              ? <CheckCircle2 size={30} />
              : <MailCheck size={30} />}
          </div>

          <h1 className="mt-7 text-3xl font-bold">
            {status === 'verified'
              ? 'Email verified!'
              : 'Email verification'}
          </h1>

          {status === 'verified' ? (
            <>
              <p className="mt-4 leading-7 text-[#647365]">
                Your Tuviora account is now active.
                Continue to your invitation or sign in.
              </p>

              <Link
                to={nextPath}
                className="mt-7 inline-flex w-full items-center justify-center rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white"
              >
                {nextPath === '/operations'
                  ? 'Continue to sign in'
                  : 'Continue to your invitation'}
              </Link>
            </>
          ) : (
            <>
              <p className="mt-4 leading-7 text-[#647365]">
                {status === 'missing'
                  ? 'This verification link is missing its token.'
                  : status === 'working'
                    ? 'Please wait while we verify your email.'
                    : status === 'error'
                      ? error
                      : 'Confirm your email address to activate your Tuviora account.'}
              </p>

              {status === 'ready' && (
                <button
                  type="button"
                  onClick={handleVerify}
                  className="mt-7 w-full rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white"
                >
                  Verify my email
                </button>
              )}

              {status === 'working' && (
                <button
                  type="button"
                  disabled
                  className="mt-7 w-full rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white opacity-60"
                >
                  Verifying…
                </button>
              )}

              <Link
                to={nextPath}
                className="mt-6 inline-flex font-semibold text-[#58761B]"
              >
                {nextPath === '/operations'
                  ? 'Continue to sign in'
                  : 'Return to your invitation'}
              </Link>
            </>
          )}
        </section>
      </div>
    </main>
  )
}
