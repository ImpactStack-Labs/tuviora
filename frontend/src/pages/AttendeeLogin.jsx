import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { loginOrganizer } from '../lib/auth'
import { safeAttendeePath } from '../lib/attendeeReturn'
import AuthCard from '../components/AuthCard'
import CredentialsForm from '../components/CredentialsForm'

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
    <AuthCard
      as="main"
      backLink={
        <Link to="/events" className="inline-flex items-center gap-2 text-sm font-semibold text-[#58761B]">
          <ArrowLeft size={17} />
          Back to events
        </Link>
      }
      eyebrow="Tuviora events"
      title="Attendee sign in"
      description="Sign in to register for events and manage your registrations."
      footer={
        <>
          New to Tuviora?{' '}
          <Link
            to={`/signup?next=${encodeURIComponent(nextPath)}`}
            className="font-semibold text-[#58761B] hover:underline"
          >
            Create an account
          </Link>
        </>
      }
    >
      <CredentialsForm
        username={username}
        onUsernameChange={(event) => setUsername(event.target.value)}
        password={password}
        onPasswordChange={(event) => setPassword(event.target.value)}
        error={error}
        loading={loading}
        onSubmit={handleSubmit}
      />
    </AuthCard>
  )
}
