import { useEffect, useMemo, useState } from 'react'
import {
  CalendarDays,
  CheckCircle2,
  RefreshCw,
  Search,
  TicketCheck,
  Users,
  XCircle,
} from 'lucide-react'
import {
  formatApiError,
  getEventRegistrations,
  getEvents,
} from '../lib/events'

function SummaryCard({ label, value, icon: Icon }) {
  return (
    <div className="rounded-2xl border border-[#E3E9DF] bg-white p-5">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm text-[#718072]">{label}</span>
        <Icon size={20} className="text-[#58761B]" />
      </div>
      <p className="text-3xl font-bold text-[#1A3F22]">{value}</p>
    </div>
  )
}

export default function EventRegistrations() {
  const [events, setEvents] = useState([])
  const [selectedEventId, setSelectedEventId] = useState('')
  const [registrations, setRegistrations] = useState([])
  const [loadingEvents, setLoadingEvents] = useState(true)
  const [loadingRegistrations, setLoadingRegistrations] = useState(false)
  const [error, setError] = useState('')
  const [registrationError, setRegistrationError] = useState(false)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let active = true

    async function loadEvents() {
      try {
        const result = await getEvents()
        const items = Array.isArray(result)
          ? result
          : result?.results || []

        if (active) {
          setEvents(items)
          if (items.length) setSelectedEventId(String(items[0].id))
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

  useEffect(() => {
    if (!selectedEventId) return

    let active = true
    setLoadingRegistrations(true)
    setError('')
    setRegistrationError(false)
    setRegistrations([])

    async function loadRegistrations() {
      try {
        const result = await getEventRegistrations(selectedEventId)
        const items = Array.isArray(result)
          ? result
          : result?.results || []

        if (active) setRegistrations(items)
      } catch (err) {
        if (active) {
          setError(formatApiError(err))
          setRegistrationError(true)
        }
      } finally {
        if (active) setLoadingRegistrations(false)
      }
    }

    loadRegistrations()
    return () => { active = false }
  }, [selectedEventId, refreshKey])

  const selectedEvent = events.find(
    (event) => String(event.id) === selectedEventId
  )

  const counts = useMemo(() => ({
    total: registrations.length,
    confirmed: registrations.filter(
      (item) => item.status === 'confirmed'
    ).length,
    cancelled: registrations.filter(
      (item) => item.status === 'cancelled'
    ).length,
  }), [registrations])

  const visibleRegistrations = useMemo(() => {
    const term = query.trim().toLowerCase()

    return registrations.filter((item) => {
      const matchesFilter = filter === 'all' || item.status === filter
      const matchesSearch = !term ||
        String(item.user).includes(term) ||
        String(item.id).includes(term)

      return matchesFilter && matchesSearch
    })
  }, [registrations, query, filter])

  return (
    <div className="mx-auto max-w-7xl space-y-7 pb-10">
      <header>
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#58761B]">
          Event management
        </p>
        <h1 className="text-3xl font-bold text-[#1A3F22] sm:text-4xl">
          Registrations
        </h1>
        <p className="mt-2 text-[#718072]">
          View and manage registration records for your events.
        </p>
      </header>

      <section className="rounded-2xl border border-[#E3E9DF] bg-white p-5">
        <label
          htmlFor="registration-event"
          className="mb-2 block text-sm font-semibold text-[#1A3F22]"
        >
          Select an event
        </label>
        <select
          id="registration-event"
          value={selectedEventId}
          onChange={(event) => {
            setSelectedEventId(event.target.value)
            setQuery('')
            setFilter('all')
          }}
          disabled={loadingEvents || !events.length}
          className="w-full rounded-xl border border-[#D5DFD0] bg-white px-4 py-3 text-[#1A3F22] focus:border-[#58761B] focus:outline-none sm:max-w-xl"
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

        {selectedEvent && (
          <p className="mt-3 flex items-center gap-2 text-sm text-[#718072]">
            <CalendarDays size={16} />
            {selectedEvent.date || 'Date not set'}
            <span className="rounded-full bg-[#EDF3E8] px-3 py-1 text-xs font-semibold capitalize text-[#58761B]">
              {selectedEvent.status}
            </span>
          </p>
        )}
      </section>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-3">
        <SummaryCard
          label="Total registrations"
          value={loadingRegistrations || registrationError ? '—' : counts.total}
          icon={Users}
        />
        <SummaryCard
          label="Confirmed"
          value={loadingRegistrations || registrationError ? '—' : counts.confirmed}
          icon={CheckCircle2}
        />
        <SummaryCard
          label="Cancelled"
          value={loadingRegistrations || registrationError ? '—' : counts.cancelled}
          icon={XCircle}
        />
      </section>

      <section className="overflow-hidden rounded-2xl border border-[#E3E9DF] bg-white">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#E3E9DF] p-5">
          <div>
            <h2 className="text-xl font-bold text-[#1A3F22]">
              Attendees
            </h2>
            <p className="mt-1 text-sm text-[#718072]">
              Registration records for the selected event
            </p>
          </div>
          <button
            type="button"
            onClick={() => setRefreshKey((value) => value + 1)}
            disabled={!selectedEventId || loadingRegistrations}
            className="inline-flex items-center gap-2 rounded-xl border border-[#D5DFD0] px-4 py-2 text-sm font-semibold text-[#1A3F22] hover:bg-[#F7F9F5] disabled:opacity-50"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        <div className="flex flex-wrap gap-3 p-5">
          <div className="relative min-w-[200px] flex-1">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[#718072]"
            />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by attendee ID"
              className="w-full rounded-xl border border-[#D5DFD0] py-3 pl-10 pr-4 text-sm focus:border-[#58761B] focus:outline-none"
            />
          </div>
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            className="rounded-xl border border-[#D5DFD0] bg-white px-4 py-3 text-sm text-[#1A3F22]"
          >
            <option value="all">All statuses</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        {loadingEvents || loadingRegistrations ? (
          <p className="p-10 text-center text-[#718072]">
            Loading registrations...
          </p>
        ) : registrationError ? (
          <p role="status" className="p-10 text-center text-[#718072]">
            Unable to load registrations. Please try refreshing.
          </p>
        ) : !events.length ? (
          <p className="p-10 text-center text-[#718072]">
            Create an event to start receiving registrations.
          </p>
        ) : !visibleRegistrations.length ? (
          <div className="flex flex-col items-center gap-3 p-10 text-center text-[#718072]">
            <TicketCheck size={34} className="text-[#58761B]" />
            <p>
              {registrations.length
                ? 'No registrations match your search or filter.'
                : 'No attendees have registered for this event yet.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[580px] text-left text-sm">
              <thead className="bg-[#F7F9F5] text-[#58715B]">
                <tr>
                  <th className="px-5 py-4 font-semibold">Attendee</th>
                  <th className="px-5 py-4 font-semibold">Registration</th>
                  <th className="px-5 py-4 font-semibold">Registered on</th>
                  <th className="px-5 py-4 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E3E9DF]">
                {visibleRegistrations.map((item) => (
                  <tr key={item.id}>
                    <td className="px-5 py-4 font-semibold text-[#1A3F22]">
                      Attendee #{item.user}
                    </td>
                    <td className="px-5 py-4 text-[#718072]">
                      #{item.id}
                    </td>
                    <td className="px-5 py-4 text-[#718072]">
                      {new Date(item.registered_at).toLocaleDateString('en-UG')}
                    </td>
                    <td className="px-5 py-4">
                      <span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${
                        item.status === 'confirmed'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-50 text-red-700'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
