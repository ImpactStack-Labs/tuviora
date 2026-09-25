import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, CalendarDays, MapPin, Ticket, Users } from 'lucide-react'
import { getCurrentUser } from '../lib/auth'
import {
  cancelMyEventRegistration,
  getMyRegistrations,
} from '../lib/events'
import { formatEventDate } from '../lib/format'
import LoadingRow from '../components/LoadingRow'

function isPastEvent(event) {
  const today = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Africa/Kampala',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())

  return event.date < today
}

export default function MyRegistrations() {
  const [user, setUser] = useState(null)
  const [registrations, setRegistrations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [workingId, setWorkingId] = useState(null)
  const [actionError, setActionError] = useState('')

  async function loadRegistrations() {
    setLoading(true)
    setError('')

    try {
      const session = await getCurrentUser()
      setUser(session.user)

      const result = await getMyRegistrations()
      setRegistrations(Array.isArray(result) ? result : result.results || [])
    } catch (err) {
      if (err.status === 401 || err.status === 403) {
        setUser(null)
        setError('Please sign in to view your registrations.')
      } else {
        setError(err.message || 'Unable to load your registrations.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRegistrations()
  }, [])

  async function handleCancel(registration) {
    if (!window.confirm(`Cancel your registration for ${registration.event.name}?`)) {
      return
    }

    setWorkingId(registration.id)
    setActionError('')

    try {
      const result = await cancelMyEventRegistration(registration.event.id)
      setRegistrations((current) =>
        current.map((item) =>
          item.id === registration.id
            ? { ...item, status: result.status, updated_at: result.updated_at }
            : item,
        ),
      )
    } catch (err) {
      setActionError(err.message || 'Unable to cancel your registration.')
    } finally {
      setWorkingId(null)
    }
  }

  const upcoming = registrations.filter(
    (item) => item.status !== 'cancelled' && !isPastEvent(item.event),
  )
  const history = registrations.filter(
    (item) => item.status === 'cancelled' || isPastEvent(item.event),
  )

  function registrationCard(item) {
    const past = isPastEvent(item.event)
    const confirmed = item.status === 'confirmed'
    const pending = item.status === 'payment_pending'

    const badgeLabel = pending
      ? 'Payment pending'
      : confirmed
        ? (past ? 'Past event' : 'Confirmed')
        : 'Cancelled'

    return (
      <article
        key={item.id}
        className="rounded-2xl border border-border-soft bg-white p-6 shadow-sm"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-[#58761B]">
              {item.event.category}
            </p>
            <h3 className="mt-2 text-xl font-bold">{item.event.name}</h3>
          </div>
          <span className={`rounded-full px-3 py-1 text-xs font-bold ${
            confirmed
              ? 'bg-green-50 text-green-800'
              : 'bg-amber-50 text-amber-800'
          }`}>
            {badgeLabel}
          </span>
        </div>

        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-3 text-sm text-[#647064]">
          <span className="inline-flex items-center gap-2">
            <CalendarDays size={17} />
            {formatEventDate(item.event.date)}
          </span>
          <span className="inline-flex items-center gap-2">
            <MapPin size={17} />
            {item.event.event_format === 'virtual'
              ? 'Virtual event'
              : item.event.venue || 'Venue to be announced'}
          </span>
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          {!past && (
            <Link
              to={`/events/${item.event.id}`}
              className="rounded-xl bg-[#1A3F22] px-5 py-3 text-sm font-semibold text-white hover:bg-[#31563A]"
            >
              View event
            </Link>
          )}
          {confirmed && !past && (
            <button
              type="button"
              onClick={() => handleCancel(item)}
              disabled={workingId !== null}
              className="rounded-xl border border-red-300 px-5 py-3 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
            >
              {workingId === item.id ? 'Cancelling...' : 'Cancel registration'}
            </button>
          )}
        </div>
      </article>
    )
  }

  return (
    <main className="min-h-screen bg-[#F7F9F5] text-[#1A3F22]">
      <header className="border-b border-border-soft bg-white px-5 py-5">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <Link to="/" className="text-2xl font-bold">
            tuviora<span className="text-[#D99201]">.</span>
          </Link>
          <Link
            to="/events"
            className="inline-flex items-center gap-2 text-sm font-semibold text-[#58761B]"
          >
            <ArrowLeft size={17} />
            Explore events
          </Link>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-12">
        <div className="mb-10">
          <p className="text-sm font-bold uppercase tracking-widest text-[#58761B]">
            Attendee dashboard
          </p>
          <h1 className="mt-3 text-3xl font-bold sm:text-4xl">My Registrations</h1>
          <p className="mt-4 text-[#647064]">
            {user
              ? `Welcome, ${user.first_name || user.username}. Manage your events in one place.`
              : 'Your upcoming events and registration history.'}
          </p>
        </div>

        {loading ? (
          <LoadingRow label="Loading your registrations..." />
        ) : error ? (
          <div role="alert" className="rounded-2xl bg-white p-7">
            <p className="text-red-700">{error}</p>
            {user ? (
              <button
                type="button"
                onClick={loadRegistrations}
                className="mt-5 rounded-xl bg-[#1A3F22] px-5 py-3 font-semibold text-white"
              >
                Try again
              </button>
            ) : (
              <Link
                to="/attendee/login?next=%2Fmy-registrations"
                className="mt-5 inline-block rounded-xl bg-[#1A3F22] px-5 py-3 font-semibold text-white"
              >
                Sign in
              </Link>
            )}
          </div>
        ) : (
          <>
            {actionError && (
              <p role="alert" className="mb-6 rounded-xl bg-red-50 p-4 text-red-700">
                {actionError}
              </p>
            )}

            <section>
              <h2 className="mb-5 flex items-center gap-2 text-2xl font-bold">
                <Ticket size={24} />
                Upcoming registrations ({upcoming.length})
              </h2>
              {upcoming.length ? (
                <div className="grid gap-5 md:grid-cols-2">
                  {upcoming.map(registrationCard)}
                </div>
              ) : (
                <div className="rounded-2xl border border-border-soft bg-white p-8">
                  <p className="text-[#647064]">You have no upcoming registrations.</p>
                  <Link
                    to="/events"
                    className="mt-4 inline-block font-semibold text-[#58761B] underline"
                  >
                    Find an event
                  </Link>
                </div>
              )}
            </section>

            <section className="mt-12">
              <h2 className="mb-5 flex items-center gap-2 text-2xl font-bold">
                <Users size={24} />
                Registration history ({history.length})
              </h2>
              {history.length ? (
                <div className="grid gap-5 md:grid-cols-2">
                  {history.map(registrationCard)}
                </div>
              ) : (
                <p className="text-[#647064]">No previous or cancelled registrations.</p>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  )
}
