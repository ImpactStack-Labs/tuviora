import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CalendarDays,
  Users,
  CreditCard,
  AlertTriangle,
  FilePenLine,
  Globe2,
  ArrowRight,
  RefreshCw,
  Plus,
  MapPin,
} from 'lucide-react'
import {
  getEvents,
  getEventRegistrations,
  formatApiError,
} from '../lib/events'
import { apiRequest } from '../lib/auth'
import { formatEventDate, formatEventTime } from '../lib/format'
import StatCard from '../components/StatCard'
import EmptyState from '../components/EmptyState'

export default function OrganizerOverview() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  const [operations, setOperations] = useState(null)
  const [operationsLoading, setOperationsLoading] = useState(false)
  const [operationsError, setOperationsError] = useState('')

  useEffect(() => {
    let active = true

    async function loadEvents() {
      setLoading(true)
      setError('')

      try {
        const result = await getEvents()
        if (active) {
          setEvents(
            Array.isArray(result) ? result : result.results || []
          )
        }
      } catch (err) {
        if (active) setError(formatApiError(err))
      } finally {
        if (active) setLoading(false)
      }
    }

    loadEvents()
    return () => {
      active = false
    }
  }, [reload])

  useEffect(() => {
    if (loading || error) return

    let active = true

    async function loadOperations() {
      setOperationsLoading(true)
      setOperationsError('')
      setOperations(null)

      const results = await Promise.allSettled(
        events.flatMap((event) => [
          getEventRegistrations(event.id),
          apiRequest(`/api/events/${event.id}/incidents/`),
        ])
      )

      if (!active) return

      const totals = {
        confirmed: 0,
        pending: 0,
        unresolved: 0,
      }

      let failures = 0

      results.forEach((result, index) => {
        if (result.status === 'rejected') {
          failures += 1
          return
        }

        const data = result.value
        const records = Array.isArray(data)
          ? data
          : Array.isArray(data?.results)
            ? data.results
            : null

        if (!records) {
          failures += 1
          return
        }

        if (index % 2 === 0) {
          totals.confirmed += records.filter(
            (registration) => registration.status === 'confirmed'
          ).length

          totals.pending += records.filter(
            (registration) => registration.status === 'payment_pending'
          ).length
        } else {
          totals.unresolved += records.filter(
            (incident) =>
              incident.status === 'open' ||
              incident.status === 'in_progress'
          ).length
        }
      })

      if (failures) {
        setOperationsError(
          `Could not load ${failures} operational data ${
            failures === 1 ? 'request' : 'requests'
          }. Retry to refresh the statistics.`
        )
      }

      if (failures === 0) {
        setOperations(totals)
      }

      setOperationsLoading(false)
    }

    loadOperations()

    return () => {
      active = false
    }
  }, [events, loading, error, reload])

  const counts = useMemo(() => ({
    total: events.length,
    published: events.filter(
      (event) => event.status === 'published'
    ).length,
    draft: events.filter(
      (event) => event.status === 'draft'
    ).length,
  }), [events])

  const upcomingEvents = useMemo(() => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    return events
      .filter((event) => {
        if (event.status !== 'published' || !event.date) return false
        const eventDate = new Date(`${event.date}T00:00:00`)
        return !Number.isNaN(eventDate.getTime()) && eventDate >= today
      })
      .sort((a, b) =>
        `${a.date}T${a.start_time || '00:00:00'}`.localeCompare(
          `${b.date}T${b.start_time || '00:00:00'}`
        )
      )
  }, [events])

  const displayedUpcomingEvents = upcomingEvents.slice(0, 4)

  const stats = [
    {
      name: 'Your events',
      value: counts.total,
      icon: CalendarDays,
      caption: 'All your events',
    },
    {
      name: 'Published',
      value: counts.published,
      icon: Globe2,
      caption: 'Visible to attendees',
    },
    {
      name: 'Drafts',
      value: counts.draft,
      icon: FilePenLine,
      caption: 'Not yet published',
    },
    {
      name: 'Upcoming',
      value: upcomingEvents.length,
      icon: CalendarDays,
      caption: 'Future published events',
    },
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-5">
        <div>
          <p className="mb-2 font-semibold text-[#58761B]">
            Overview
          </p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Your event workspace
          </h1>
          <p className="mt-3 text-[#647064]">
            A clear view of your events and what is coming up.
          </p>
        </div>

        <Link
          to="/operations/events"
          className="tuviora-button-primary"
        >
          My Events <ArrowRight size={18} />
        </Link>
      </div>

      {error && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-red-200 bg-red-50 p-5 text-red-800"
        >
          <p>{error}</p>
          <button
            type="button"
            onClick={() => setReload((value) => value + 1)}
            className="inline-flex items-center gap-2 font-semibold underline"
          >
            <RefreshCw size={17} />
            Try again
          </button>
        </div>
      )}

      {loading ? (
        <div
          role="status"
          className="rounded-2xl border border-border-soft bg-white p-8 text-center text-[#647064]"
        >
          <RefreshCw className="mx-auto mb-3 animate-spin" size={24} />
          Loading your event dashboard...
        </div>
      ) : !error && (
        <>
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
            {stats.map(({ name, value, icon, caption }) => (
              <StatCard
                key={name}
                label={name}
                value={value}
                icon={icon}
                caption={caption}
              />
            ))}
          </div>

          <section className="tuviora-surface-card p-6 sm:p-8">
            <div className="mb-6">
              <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-[#58761B]">
                Live event data
              </p>
              <h2 className="text-2xl font-bold">
                Operational summary
              </h2>
              <p className="mt-2 text-sm leading-6 text-[#647064]">
                Registration, payment and incident figures across your events.
              </p>
            </div>

            {operationsLoading ? (
              <p role="status" className="flex items-center gap-3 text-[#647064]">
                <RefreshCw size={19} className="animate-spin" />
                Loading operational statistics...
              </p>
            ) : operationsError ? (
              <div
                role="alert"
                className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-amber-900"
              >
                <p>{operationsError}</p>
                <button
                  type="button"
                  onClick={() => setReload((value) => value + 1)}
                  className="mt-3 font-semibold underline"
                >
                  Retry
                </button>
              </div>
            ) : operations ? (
              <div className="grid gap-5 sm:grid-cols-3">
                <StatCard
                  label="Confirmed registrations"
                  value={operations.confirmed}
                  icon={Users}
                  caption="Confirmed attendee registrations"
                />
                <StatCard
                  label="Pending payments"
                  value={operations.pending}
                  icon={CreditCard}
                  caption="Registrations awaiting payment"
                />
                <StatCard
                  label="Unresolved incidents"
                  value={operations.unresolved}
                  icon={AlertTriangle}
                  caption="Open or in-progress reports"
                />
              </div>
            ) : null}
          </section>

          <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
            <section className="tuviora-surface-card p-6 sm:p-8">
              <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xl font-bold">Upcoming events</h2>
                <Link
                  to="/operations/events"
                  className="inline-flex items-center gap-2 font-semibold text-[#58761B] hover:underline"
                >
                  View all <ArrowRight size={17} />
                </Link>
              </div>

              {upcomingEvents.length ? (
                <div className="space-y-4">
                  {displayedUpcomingEvents.map((event) => (
                    <div
                      key={event.id}
                      className="rounded-xl border border-border-soft bg-[#F8F9F5] p-5"
                    >
                      <h3 className="font-bold text-[#1A3F22]">
                        {event.name}
                      </h3>
                      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-[#526052]">
                        <span className="inline-flex items-center gap-2">
                          <CalendarDays size={16} />
                          {formatEventDate(event.date)}
                        </span>
                        <span>
                          {formatEventTime(event.start_time)}
                        </span>
                        <span className="inline-flex items-center gap-2">
                          <MapPin size={16} />
                          {event.event_format === 'virtual'
                            ? 'Online'
                            : event.venue || 'Venue to be announced'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={CalendarDays}
                  title="No upcoming published events"
                  description="Your upcoming published events will appear here."
                  bordered={false}
                />
              )}
            </section>

            <section className="tuviora-surface-card p-6 sm:p-8">
              <h2 className="text-xl font-bold">Quick actions</h2>
              <p className="mt-3 leading-7 text-[#647064]">
                Keep planning and managing your events.
              </p>

              <div className="mt-6 space-y-3">
                <Link
                  to="/operations/events/new"
                  className="tuviora-button-primary w-full"
                >
                  <Plus size={18} />
                  Create an event
                </Link>
                <Link
                  to="/operations/events"
                  className="tuviora-button-secondary w-full"
                >
                  <CalendarDays size={18} />
                  Manage your events
                </Link>
                <Link
                  to="/operations/incidents"
                  className="tuviora-button-secondary w-full"
                >
                  Review incidents
                  <ArrowRight size={17} />
                </Link>
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  )
}
