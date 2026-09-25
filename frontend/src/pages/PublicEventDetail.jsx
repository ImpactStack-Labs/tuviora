import TuvioraLogo from '../components/TuvioraLogo'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCurrentUser } from '../lib/auth'
import {
  registerForEvent,
  getMyEventRegistration,
  cancelMyEventRegistration,
  initiateRegistrationPayment,
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
import RegistrationTicket from '../components/RegistrationTicket'

export default function PublicEventDetail() {
  const { eventId } = useParams()
  const [event, setEvent] = useState(null)
  const [user, setUser] = useState(null)
  const [registration, setRegistration] = useState(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [registrationError, setRegistrationError] = useState('')
  const [selectedTicketTypeId, setSelectedTicketTypeId] = useState(null)
  const [paymentMethod, setPaymentMethod] = useState('mobile_money')
  const [paymentPhone, setPaymentPhone] = useState('')
  const [paymentError, setPaymentError] = useState('')
  const [payingNow, setPayingNow] = useState(false)
  const [polling, setPolling] = useState(false)
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

  useEffect(() => {
    if (!polling) return undefined

    const interval = setInterval(async () => {
      try {
        const latest = await getMyEventRegistration(eventId)
        setRegistration(latest)
        if (latest.status !== 'payment_pending') {
          setPolling(false)
        }
      } catch {
        // Keep polling; a transient error shouldn't stop the check.
      }
    }, 4000)

    return () => clearInterval(interval)
  }, [polling, eventId])

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

  async function handlePay() {
    setPayingNow(true)
    setPaymentError('')

    try {
      const payment = await initiateRegistrationPayment(eventId, {
        method: paymentMethod,
        phoneNumber: paymentMethod === 'mobile_money' ? paymentPhone : undefined,
      })

      if (payment.redirect_url) {
        window.location.href = payment.redirect_url
        return
      }

      setPolling(true)
    } catch (err) {
      setPaymentError(err.message || 'Unable to start payment. Please try again.')
    } finally {
      setPayingNow(false)
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
      <header className="sticky top-0 z-40 border-b border-border-soft bg-white/95 px-5 backdrop-blur-xl">
        <div className="tuviora-container flex min-h-20 flex-wrap items-center justify-between gap-4 py-4">
          <TuvioraLogo />
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

      <div className="mx-auto max-w-6xl px-5 py-8 sm:py-12">
        {loading ? (
          <LoadingRow label="Loading event..." />
        ) : error ? (
          <div role="alert" className="rounded-2xl bg-white p-8 text-red-700">
            {error}
          </div>
        ) : event && (
          <div className="overflow-hidden rounded-3xl border border-border-soft bg-white shadow-sm">
            <section className="bg-[#1A3F22] px-6 py-12 text-white sm:px-12 sm:py-16">
              <p className="text-sm font-semibold uppercase tracking-widest text-[#E9B64E]">
                {event.category}
              </p>
              <h1 className="mt-4 max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
                {event.name}
              </h1>
              <p className="mt-5 max-w-3xl leading-8 text-white/80">
                {event.description || 'Join us for this upcoming event.'}
              </p>
            </section>

            <section className="grid gap-10 p-6 sm:p-10 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.9fr)] lg:gap-14">
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

              <div className="h-fit rounded-2xl border border-border-soft bg-[#F7F9F5] p-6 shadow-sm sm:p-8">
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
                              className={`flex cursor-pointer flex-wrap items-center justify-between gap-3 rounded-xl border p-4 transition-colors ${
                                selectedTicketTypeId === ticket.id
                                  ? 'border-[#58761B] bg-[#EDF3E8] ring-1 ring-[#58761B]/20'
                                  : 'border-border-soft bg-white hover:border-[#B9C9B3]'
                              }`}
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
                      <div className="mt-6 space-y-4">
                        <div
                          role="status"
                          className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"
                        >
                          Your spot is reserved — complete payment of{' '}
                          {registration.amount_due} {registration.currency}{' '}
                          to confirm it.
                        </div>

                        {polling && (
                          <p role="status" className="text-sm text-[#647064]">
                            Waiting for payment confirmation...
                          </p>
                        )}

                        <div className="flex flex-wrap gap-5 rounded-xl border border-border-soft bg-white p-4">
                          <label className="flex items-center gap-2">
                            <input
                              type="radio"
                              checked={paymentMethod === 'mobile_money'}
                              onChange={() => setPaymentMethod('mobile_money')}
                            />
                            Mobile Money
                          </label>
                          <label className="flex items-center gap-2">
                            <input
                              type="radio"
                              checked={paymentMethod === 'card'}
                              onChange={() => setPaymentMethod('card')}
                            />
                            Card
                          </label>
                        </div>

                        {paymentMethod === 'mobile_money' && (
                          <input
                            value={paymentPhone}
                            onChange={(event) => setPaymentPhone(event.target.value)}
                            placeholder="+256700123456"
                            className="min-h-12 w-full rounded-xl border border-[#DCE5D8] bg-white px-4 py-3 text-base focus:border-[#58761B] focus:outline-none focus:ring-2 focus:ring-[#58761B]/15"
                          />
                        )}

                        <button
                          type="button"
                          onClick={handlePay}
                          disabled={payingNow || polling}
                          className="w-full rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white hover:bg-[#31563A] disabled:opacity-60"
                        >
                          {payingNow
                            ? 'Starting payment...'
                            : paymentMethod === 'card'
                              ? 'Pay by card'
                              : 'Send payment prompt'}
                        </button>

                        {paymentError && (
                          <p role="alert" className="text-sm text-red-700">
                            {paymentError}
                          </p>
                        )}
                      </div>
                    ) : registration?.status === 'confirmed' ? (
                      <>
                        <div
                          role="status"
                          className="mt-6 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800"
                        >
                          Your registration is confirmed.
                        </div>

                        <RegistrationTicket eventId={eventId} />

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
