import { useEffect, useState } from 'react'
import TicketQrScanner from '../components/TicketQrScanner'
import {
  CheckCircle2,
  ScanLine,
  TicketCheck,
} from 'lucide-react'
import {
  checkInEventTicket,
  formatApiError,
  getEvents,
} from '../lib/events'

export default function EventAttendance() {
  const [events, setEvents] = useState([])
  const [selectedEventId, setSelectedEventId] = useState('')
  const [token, setToken] = useState('')
  const [loadingEvents, setLoadingEvents] = useState(true)
  const [checkingIn, setCheckingIn] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  useEffect(() => {
    let active = true

    async function loadEvents() {
      try {
        const response = await getEvents()
        const items = Array.isArray(response)
          ? response
          : response?.results || []

        if (!active) return

        setEvents(items)
        if (items.length) {
          setSelectedEventId(String(items[0].id))
        }
      } catch (err) {
        if (active) setError(formatApiError(err))
      } finally {
        if (active) setLoadingEvents(false)
      }
    }

    loadEvents()
    return () => { active = false }
  }, [])

  async function handleCheckIn(event) {
    event.preventDefault()

    if (!selectedEventId || !token.trim() || checkingIn) return

    setCheckingIn(true)
    setError('')
    setResult(null)

    try {
      const response = await checkInEventTicket(
        selectedEventId,
        token.trim(),
      )

      setResult(response)
      setToken('')
    } catch (err) {
      if (err.status === 409) {
        setError('This ticket has already been checked in.')
      } else if (err.status === 404) {
        setError('Ticket not found for the selected event.')
      } else if (err.status === 403) {
        setError(
          'Check-in denied. Your account may lack permission, or the registration may not be confirmed.',
        )
      } else {
        setError(formatApiError(err))
      }
    } finally {
      setCheckingIn(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-7 pb-10">
      <header>
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#58761B]">
          Event operations
        </p>
        <h1 className="text-3xl font-bold text-[#1A3F22] sm:text-4xl">
          Attendance
        </h1>
        <p className="mt-2 text-[#718072]">
          Validate tickets and check in confirmed attendees.
        </p>
      </header>

      <section className="rounded-2xl border border-border-soft bg-white p-6">
        <label
          htmlFor="attendance-event"
          className="mb-2 block text-sm font-semibold"
        >
          Select an event
        </label>

        <select
          id="attendance-event"
          value={selectedEventId}
          onChange={(event) => {
            setSelectedEventId(event.target.value)
            setToken('')
            setError('')
            setResult(null)
          }}
          disabled={loadingEvents || !events.length}
          className="w-full rounded-xl border border-border-soft bg-white px-4 py-3 sm:max-w-xl"
        >
          {!events.length && (
            <option value="">
              {loadingEvents ? 'Loading events...' : 'No events available'}
            </option>
          )}
          {events.map((event) => (
            <option key={event.id} value={String(event.id)}>
              {event.name}
            </option>
          ))}
        </select>
      </section>

      <section className="rounded-2xl border border-border-soft bg-white p-6">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-xl bg-[#EDF3E8] p-3 text-[#58761B]">
            <ScanLine size={25} aria-hidden="true" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-[#1A3F22]">
              Check in an attendee
            </h2>
            <p className="text-sm text-[#718072]">
              Enter the QR token or ticket reference.
            </p>
          </div>
        </div>

        <TicketQrScanner
          key={selectedEventId}
          disabled={!selectedEventId || checkingIn}
          onScan={(decodedToken) => {
            setToken(decodedToken)
            setError('')
            setResult(null)
          }}
        />

        <form onSubmit={handleCheckIn} className="space-y-4">
          <div>
            <label
              htmlFor="attendance-token"
              className="mb-2 block text-sm font-semibold"
            >
              Ticket reference
            </label>
            <input
              id="attendance-token"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              placeholder="Paste or enter ticket reference"
              autoComplete="off"
              spellCheck={false}
              required
              className="w-full rounded-xl border border-border-soft px-4 py-3 font-mono text-sm focus:border-[#58761B]"
            />
          </div>

          <button
            type="submit"
            disabled={!selectedEventId || !token.trim() || checkingIn}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white hover:bg-[#31563A] disabled:opacity-50 sm:w-auto"
          >
            <TicketCheck size={19} aria-hidden="true" />
            {checkingIn ? 'Checking ticket...' : 'Confirm check-in'}
          </button>
        </form>

        {error && (
          <div
            role="alert"
            className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
          >
            {error}
          </div>
        )}

        {result && (
          <div
            role="status"
            className="mt-5 rounded-xl border border-green-200 bg-green-50 p-5 text-green-800"
          >
            <div className="flex items-center gap-2 font-bold">
              <CheckCircle2 size={22} aria-hidden="true" />
              Check-in successful
            </div>
            <p className="mt-2">Attendee: {result.attendee}</p>
            <p className="mt-1 break-all text-sm">
              Reference: {result.reference}
            </p>
          </div>
        )}
      </section>
    </div>
  )
}
