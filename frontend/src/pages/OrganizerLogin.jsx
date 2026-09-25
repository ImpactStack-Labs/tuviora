import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getCurrentUser, loginOrganizer } from '../lib/auth'
import AuthCard from '../components/AuthCard'
import CredentialsForm from '../components/CredentialsForm'

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
    <AuthCard
      eyebrow="Tuviora"
      title="Organizer sign in"
      description="Sign in to manage your events, preparations and communications."
      footer={
        <>
          New to Tuviora?{' '}
          <Link to="/signup" className="font-semibold text-[#58761B] hover:underline">
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
