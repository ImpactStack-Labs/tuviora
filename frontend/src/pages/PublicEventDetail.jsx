import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCurrentUser } from '../lib/auth'
import {
  registerForEvent,
  getMyEventRegistration,
  cancelMyEventRegistration,
} from '../lib/events'
import { clearAttendeeReturn } from '../lib/attendeeReturn'
import {
  ArrowLeft,
  CalendarDays,
  Clock3,
  MapPin,
  Users,
} from 'lucide-react'
import { formatEventDate, formatEventTime } from '../lib/format'
import LoadingRow from '../components/LoadingRow'

export default function PublicEventDetail() {
  const { eventId } = useParams()
  const [event, setEvent] = useState(null)
  const [user, setUser] = useState(null)
  const [registration, setRegistration] = useState(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [registrationError, setRegistrationError] = useState('')
  const [selectedTicketTypeId, setSelectedTicketTypeId] = useState(null)
  const [working, setWorking] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    async function loadEvent() {
      setLoading(true)
      setError('')

      try {
        const response = await fetch(`/api/events/public/${eventId}/`, {
          signal: controller.signal,
          headers: { Accept: 'application/json' },
        })

        if (response.status === 404) {
          throw new Error('This event is unavailable or no longer published.')
        }

        if (!response.ok) {
          throw new Error('Unable to load this event.')
        }

        const selected = await response.json()
        setEvent(selected)
        if (selected.ticket_types?.length) {
          setSelectedTicketTypeId(selected.ticket_types[0].id)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message)
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    loadEvent()
    return () => controller.abort()
  }, [eventId])

  useEffect(() => {
    let active = true

    async function checkSession() {
      setCheckingSession(true)
      setRegistrationError('')

      try {
        const result = await getCurrentUser()

        if (!active) return

        setUser(result.user)
        clearAttendeeReturn()

        try {
          const existing = await getMyEventRegistration(eventId)

          if (active) {
            setRegistration(existing)
          }
        } catch (err) {
          if (active && err.status !== 404) {
            setRegistrationError(
              err.message || 'Unable to check your registration.',
            )
          }
        }
      } catch (err) {
        if (active && err.status !== 401 && err.status !== 403) {
          setRegistrationError(
            'Unable to check your session. Please refresh the page.',
          )
        }
      } finally {
        if (active) setCheckingSession(false)
      }
    }

    checkSession()

    return () => {
      active = false
    }
  }, [eventId])

  async function handleRegister() {
    setWorking(true)
    setRegistrationError('')

    try {
      const result = await registerForEvent(eventId, selectedTicketTypeId)
      setRegistration(result)
    } catch (err) {
      setRegistrationError(
        err.message || 'Unable to register. Please try again.',
      )

      if (err.status === 409) {
        try {
          const existing = await getMyEventRegistration(eventId)
          setRegistration(existing)
        } catch {
          // Keep the original registration error visible.
        }
      }
    } finally {
      setWorking(false)
    }
  }

  async function handleCancel() {
    if (!window.confirm('Cancel your registration for this event?')) {
      return
    }

    setWorking(true)
    setRegistrationError('')

    try {
      const result = await cancelMyEventRegistration(eventId)
      setRegistration(result)
    } catch (err) {
      setRegistrationError(
        err.message || 'Unable to cancel your registration.',
      )
    } finally {
      setWorking(false)
    }
  }

  return (
    <main className="min-h-screen bg-[#F7F9F5] text-[#1A3F22]">
      <header className="border-b border-border-soft bg-white px-5 py-5">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link to="/" className="text-2xl font-bold">
            tuviora<span className="text-[#D99201]">.</span>
          </Link>
          <nav className="flex flex-wrap items-center gap-5">
            <Link
              to="/my-registrations"
              className="text-sm font-semibold text-[#58761B] hover:underline"
            >
              My Registrations
            </Link>
            <Link
              to="/events"
              className="inline-flex items-center gap-2 text-sm font-semibold text-[#58761B] hover:underline"
            >
              <ArrowLeft size={17} />
              All events
            </Link>
          </nav>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-12">
        {loading ? (
          <LoadingRow label="Loading event..." />
        ) : error ? (
          <div role="alert" className="rounded-2xl bg-white p-8 text-red-700">
            {error}
          </div>
        ) : event && (
          <div className="overflow-hidden rounded-3xl border border-border-soft bg-white shadow-sm">
            <section className="bg-[#1A3F22] px-7 py-12 text-white sm:px-12">
              <p className="text-sm font-semibold uppercase tracking-widest text-[#E9B64E]">
                {event.category}
              </p>
              <h1 className="mt-4 text-4xl font-bold sm:text-5xl">
                {event.name}
              </h1>
              <p className="mt-5 max-w-3xl leading-8 text-white/80">
                {event.description || 'Join us for this upcoming event.'}
              </p>
            </section>

            <section className="grid gap-10 p-7 sm:p-12 md:grid-cols-2">
              <div className="space-y-6">
                <h2 className="text-2xl font-bold">Event details</h2>

                <p className="flex items-center gap-3">
                  <CalendarDays className="text-[#58761B]" />
                  {formatEventDate(event.date)}
                </p>

                <p className="flex items-center gap-3">
                  <Clock3 className="text-[#58761B]" />
                  {formatEventTime(event.start_time)} – {formatEventTime(event.end_time)}
                </p>

                <p className="flex items-center gap-3">
                  <MapPin className="text-[#58761B]" />
                  {event.event_format === 'virtual'
                    ? 'Virtual event'
                    : event.venue || 'Venue to be announced'}
                </p>

                {event.capacity != null && (
                  <p className="flex items-center gap-3">
                    <Users className="text-[#58761B]" />
                    Capacity: {event.capacity}
                  </p>
                )}
              </div>

              <div className="rounded-2xl border border-border-soft bg-[#F7F9F5] p-7">
                <h2 className="text-2xl font-bold">Join this event</h2>
                {checkingSession ? (
                  <p role="status" className="mt-4 text-[#647064]">
                    Checking your registration...
                  </p>
                ) : user ? (
                  <>
                    <p className="mt-3 leading-7 text-[#647064]">
                      Signed in as {user.first_name || user.username}.
                    </p>

                    {event.ticket_types?.length > 0 &&
                      (!registration || registration.status === 'cancelled') && (
                        <fieldset className="mt-6 space-y-3">
                          <legend className="font-semibold">
                            Choose a ticket
                          </legend>
                          {event.ticket_types.map((ticket) => (
                            <label
                              key={ticket.id}
                              className="flex items-center justify-between rounded-xl border border-border-soft p-4"
                            >
                              <span className="flex items-center gap-3">
                                <input
                                  type="radio"
                                  name="ticket_type"
                                  checked={selectedTicketTypeId === ticket.id}
                                  onChange={() =>
                                    setSelectedTicketTypeId(ticket.id)
                                  }
                                />
                                {ticket.name}
                              </span>
                              <span className="font-semibold">
                                {Number(ticket.price) > 0
                                  ? `${ticket.price} ${ticket.currency}`
                                  : 'Free'}
                              </span>
                            </label>
                          ))}
                        </fieldset>
                      )}

                    {registration?.status === 'payment_pending' ? (
                      <div
                        role="status"
                        className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
                      >
                        Your spot is reserved. Payment collection is
                        coming soon — you'll be notified how to pay.
                      </div>
                    ) : registration?.status === 'confirmed' ? (
                      <>
                        <div
                          role="status"
                          className="mt-6 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800"
                        >
                          Your registration is confirmed.
                        </div>

                        <button
                          type="button"
                          onClick={handleCancel}
                          disabled={working}
                          className="mt-5 w-full rounded-xl border border-red-300 px-5 py-3.5 font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
                        >
                          {working ? 'Cancelling...' : 'Cancel registration'}
                        </button>
                      </>
                    ) : (
                      <>
                        {registration?.status === 'cancelled' && (
                          <p className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
                            Your previous registration was cancelled.
                            You can register again if places are available.
                          </p>
                        )}

                        <button
                          type="button"
                          onClick={handleRegister}
                          disabled={working || Boolean(registrationError)}
                          className="mt-7 w-full rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white hover:bg-[#31563A] disabled:opacity-60"
                        >
                          {working
                            ? 'Processing...'
                            : registration?.status === 'cancelled'
                              ? 'Register again'
                              : 'Register for this event'}
                        </button>
                      </>
                    )}
                  </>
                ) : (
                  <>
                    <p className="mt-3 leading-7 text-[#647064]">
                      Sign in to register and manage your attendance.
                    </p>

                    <Link
                      to={`/attendee/login?next=${encodeURIComponent(`/events/${event.id}`)}`}
                      className="mt-7 inline-flex w-full items-center justify-center rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white hover:bg-[#31563A]"
                    >
                      Sign in to continue
                    </Link>

                    <Link
                      to={`/signup?next=${encodeURIComponent(`/events/${event.id}`)}`}
                      className="mt-4 inline-flex w-full items-center justify-center rounded-xl border border-[#B9C9B3] px-5 py-3.5 font-semibold text-[#1A3F22]"
                    >
                      Create an account
                    </Link>
                  </>
                )}

                {registrationError && (
                  <p
                    role="alert"
                    className="mt-5 rounded-xl bg-red-50 p-4 text-sm text-red-700"
                  >
                    {registrationError}
                  </p>
                )}
              </div>
            </section>
          </div>
        )}
      </div>
    </main>
  )
}
