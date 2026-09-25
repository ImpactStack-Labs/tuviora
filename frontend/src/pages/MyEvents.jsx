import { formatEventTimezone } from '../components/EventTimezone'
import { formatEventDate, formatEventTime } from '../lib/format'
import StatCard from '../components/StatCard'
import LoadingRow from '../components/LoadingRow'
import { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FilePenLine,
  MapPin,
  Plus,
  Search,
  Video,
  X,
} from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { getEvents, publishEvent, formatApiError } from '../lib/events'

const statusStyles = {
  published: 'bg-[#EDF6E9] text-[#356B35]',
  draft: 'bg-[#FFF4DE] text-[#956300]',
  cancelled: 'bg-red-50 text-red-700',
  completed: 'bg-slate-100 text-slate-700',
}

const categoryStyles =
  'bg-[#F0F4E9] text-[#58761B]'

function EventCard({ event, onPublish, publishingId, onView }) {
  const isDraft = event.status === 'draft'
  const isOnline = event.event_format === 'virtual'
  const isHybrid = event.event_format === 'hybrid'

  const location = isOnline
    ? event.online_platform || 'Online event'
    : event.venue || 'Venue not set'

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-2xl border border-border-soft bg-white shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-[#B8CDA9] hover:shadow-md">
      <div className="h-1.5 bg-[#58761B]" />

      <div className="flex flex-1 flex-col p-5 sm:p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${categoryStyles}`}>
            {event.category
              ? event.category.charAt(0).toUpperCase() + event.category.slice(1)
              : 'Event'}
          </span>

          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              statusStyles[event.status] || statusStyles.draft
            }`}
          >
            {event.status
              ? event.status.charAt(0).toUpperCase() + event.status.slice(1)
              : 'Draft'}
          </span>
        </div>

        <h3 className="text-xl font-bold leading-snug text-[#1A3F22]">
          {event.name}
        </h3>

        <p className="mt-2 line-clamp-2 min-h-10 text-sm leading-6 text-[#647064]">
          {event.description || 'No description added yet.'}
        </p>

        <div className="mt-5 space-y-3 rounded-xl bg-[#F7F9F5] p-4">
          <div className="flex items-start gap-3">
            <CalendarDays
              size={18}
              className="mt-0.5 shrink-0 text-[#58761B]"
            />
            <div>
              <p className="text-xs font-medium text-text-muted">
                Event date
              </p>
              <p className="mt-0.5 text-sm font-semibold text-[#243B29]">
                {formatEventDate(event.date)}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <Clock3
              size={18}
              className="mt-0.5 shrink-0 text-[#58761B]"
            />
            <div>
              <p className="text-xs font-medium text-text-muted">
                Start and end time
              </p>
              <p className="mt-0.5 text-sm font-semibold text-[#243B29]">
                {formatEventTime(event.start_time)}
                <span className="mx-2 text-[#9BA99A]">–</span>
                {formatEventTime(event.end_time)}
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({formatEventTimezone(
                    event.timezone_name,
                    event.date,
                  )})
                </span>
              </p>
              <p className="mt-0.5 text-xs text-text-muted">
                Event's local time
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            {isOnline ? (
              <Video
                size={18}
                className="mt-0.5 shrink-0 text-[#58761B]"
              />
            ) : (
              <MapPin
                size={18}
                className="mt-0.5 shrink-0 text-[#58761B]"
              />
            )}

            <div className="min-w-0">
              <p className="text-xs font-medium text-text-muted">
                {isOnline
                  ? 'Online platform'
                  : isHybrid
                    ? 'Venue and online'
                    : 'Venue'}
              </p>

              <p className="mt-0.5 break-words text-sm font-semibold text-[#243B29]">
                {location}
              </p>

              {isHybrid && event.online_platform && (
                <p className="mt-1 text-xs text-[#647064]">
                  Also online via {event.online_platform}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-[#E8EDE5] pt-5">
          <span className="text-xs font-medium text-text-muted">
            Event ID: {event.id}
          </span>

          <div className="flex flex-wrap items-center gap-2">
            {isDraft && (
              <button
                type="button"
                onClick={() => onPublish(event)}
                disabled={publishingId !== null}
                className="rounded-xl bg-[#1A3F22] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#315A39] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#58761B] disabled:cursor-wait disabled:opacity-60"
              >
                {publishingId === event.id
                  ? 'Publishing...'
                  : 'Publish'}
              </button>
            )}

            <button
              type="button"
              onClick={() => onView(event)}
              className="inline-flex items-center gap-2 rounded-xl border border-border-soft px-4 py-2.5 text-sm font-semibold text-[#1A3F22] transition hover:bg-[#F0F5EB] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#58761B]"
            >
              View details
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </article>
  )
}

function EventDetailsModal({ event, onClose, onPublish, publishingId }) {
  useEffect(() => {
    if (!event) return undefined

    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [event, onClose])

  if (!event) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#102616]/60 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="event-details-title"
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl sm:p-8"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <span
              className={`inline-block rounded-full px-3 py-1 text-xs font-semibold ${
                statusStyles[event.status] || statusStyles.draft
              }`}
            >
              {event.status}
            </span>

            <h2
              id="event-details-title"
              className="mt-3 text-2xl font-bold text-[#1A3F22]"
            >
              {event.name}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close event details"
            className="rounded-lg p-2 text-[#647064] hover:bg-[#F0F4ED]"
          >
            <X size={20} />
          </button>
        </div>

        <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-[#647064]">
          {event.description || 'No description provided.'}
        </p>

        <div className="mt-6 grid gap-4 rounded-xl bg-[#F7F9F5] p-5 sm:grid-cols-2">
          <div>
            <p className="text-xs text-text-muted">Category</p>
            <p className="mt-1 font-semibold capitalize text-[#1A3F22]">
              {event.category}
            </p>
          </div>

          <div>
            <p className="text-xs text-text-muted">Date</p>
            <p className="mt-1 font-semibold text-[#1A3F22]">
              {formatEventDate(event.date)}
            </p>
          </div>

          <div>
            <p className="text-xs text-text-muted">Start time</p>
            <p className="mt-1 font-semibold text-[#1A3F22]">
              {formatEventTime(event.start_time)}
            </p>
          </div>

          <div>
            <p className="text-xs text-text-muted">End time</p>
            <p className="mt-1 font-semibold text-[#1A3F22]">
              {formatEventTime(event.end_time)}
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({formatEventTimezone(
                    event.timezone_name,
                    event.date,
                  )})
                </span>
            </p>
          </div>

          <div>
            <p className="text-xs text-text-muted">Venue</p>
            <p className="mt-1 font-semibold text-[#1A3F22]">
              {event.venue || 'Online'}
            </p>
          </div>

          <div>
            <p className="text-xs text-text-muted">Capacity</p>
            <p className="mt-1 font-semibold text-[#1A3F22]">
              {event.capacity ?? 'Not specified'}
            </p>
          </div>

          {event.online_platform && (
            <div className="sm:col-span-2">
              <p className="text-xs text-text-muted">Online platform</p>
              <p className="mt-1 font-semibold text-[#1A3F22]">
                {event.online_platform}
              </p>
            </div>
          )}
        </div>

        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-border-soft px-5 py-3 text-sm font-semibold text-[#1A3F22] hover:bg-[#F7F9F5]"
          >
            Close
          </button>

          {event.status === 'draft' && (
            <button
              type="button"
              disabled={publishingId !== null}
              onClick={() => onPublish(event)}
              className="rounded-xl bg-[#1A3F22] px-5 py-3 text-sm font-semibold text-white hover:bg-[#315A39] disabled:opacity-60"
            >
              Publish event
            </button>
          )}
        </div>
      </section>
    </div>
  )
}

function PublishModal({ event, onCancel, onConfirm, publishing }) {
  useEffect(() => {
    if (!event || publishing) return undefined

    function handleKeyDown(e) {
      if (e.key === 'Escape') onCancel()
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [event, publishing, onCancel])

  if (!event) return null

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-[#102616]/60 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (!publishing && e.target === e.currentTarget) onCancel()
      }}
    >
      <section
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="publish-title"
        aria-describedby="publish-description"
        className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl bg-white p-6 shadow-2xl sm:p-8"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#EDF6E9] text-[#356B35]">
          <CheckCircle2 size={25} />
        </div>

        <h2
          id="publish-title"
          className="mt-5 text-2xl font-bold text-[#1A3F22]"
        >
          Publish your event?
        </h2>

        <p
          id="publish-description"
          className="mt-3 text-sm leading-6 text-[#647064]"
        >
          Once published, your event's details will become
          available through Tuviora's public Voice lookup.
        </p>

        <div className="mt-5 rounded-xl border border-border-soft bg-[#F7F9F5] p-4">
          <p className="font-bold text-[#1A3F22]">
            {event.name}
          </p>

          <p className="mt-2 text-sm text-[#647064]">
            {formatEventDate(event.date)}
          </p>

          <p className="mt-1 text-sm text-[#647064]">
            {formatEventTime(event.start_time)}
            {' – '}
            {formatEventTime(event.end_time)}
                <span className="ml-2 text-sm font-normal text-gray-500">
                  ({formatEventTimezone(
                    event.timezone_name,
                    event.date,
                  )})
                </span>
          </p>

          <p className="mt-1 text-sm text-[#647064]">
            {event.venue || event.online_platform || 'Online event'}
          </p>
        </div>

        <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <button
            type="button"
            disabled={publishing}
            onClick={onCancel}
            className="rounded-xl border border-border-soft px-5 py-3 text-sm font-semibold text-[#1A3F22] hover:bg-[#F7F9F5] disabled:opacity-60"
          >
            Cancel
          </button>

          <button
            type="button"
            disabled={publishing}
            onClick={onConfirm}
            className="rounded-xl bg-[#1A3F22] px-5 py-3 text-sm font-semibold text-white hover:bg-[#315A39] disabled:cursor-wait disabled:opacity-60"
          >
            {publishing ? 'Publishing...' : 'Publish event'}
          </button>
        </div>
      </section>
    </div>
  )
}

export default function MyEvents() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const [publishingId, setPublishingId] = useState(null)
  const [eventToPublish, setEventToPublish] = useState(null)
  const [selectedEvent, setSelectedEvent] = useState(null)

  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    let active = true

    async function loadEvents() {
      try {
        const result = await getEvents()

        if (active) {
          setEvents(
            Array.isArray(result)
              ? result
              : result.results || []
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
  }, [])

  const visibleEvents = useMemo(() => {
    const term = query.trim().toLowerCase()

    return events.filter((event) => {
      const matchesFilter =
        filter === 'all' || event.status === filter

      const matchesSearch =
        !term ||
        [
          event.name,
          event.category,
          event.venue,
          event.description,
        ]
          .filter(Boolean)
          .some((value) =>
            value.toLowerCase().includes(term)
          )

      return matchesFilter && matchesSearch
    })
  }, [events, query, filter])

  const counts = useMemo(() => ({
    total: events.length,
    published: events.filter(
      (event) => event.status === 'published'
    ).length,
    draft: events.filter(
      (event) => event.status === 'draft'
    ).length,
  }), [events])

  function openPublishModal(event) {
    setSelectedEvent(null)
    setEventToPublish(event)
    setError('')
  }

  function closePublishModal() {
    if (publishingId !== null) return
    setEventToPublish(null)
  }

  async function confirmPublish() {
    if (!eventToPublish || publishingId !== null) return

    const event = eventToPublish

    setPublishingId(event.id)
    setError('')
    setNotice('')

    try {
      const updated = await publishEvent(event.id)

      setEvents((current) =>
        current.map((item) =>
          item.id === updated.id ? updated : item
        )
      )

      setSelectedEvent(null)
      setEventToPublish(null)
      setNotice(`"${updated.name}" has been published successfully.`)

      // Remove any outdated "created as a draft" message.
      if (location.state?.message) {
        navigate(location.pathname, {
          replace: true,
          state: null,
        })
      }
    } catch (err) {
      setError(formatApiError(err))
      setEventToPublish(null)
    } finally {
      setPublishingId(null)
    }
  }

  const creationNotice =
    notice ? null : location.state?.message

  return (
    <div className="mx-auto w-full max-w-7xl space-y-8 pb-10">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-[#58761B]">
            Organizer workspace
          </p>

          <h1 className="text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
            My Events
          </h1>

          <p className="mt-3 text-sm leading-6 text-[#647064] sm:text-base">
            Create, organize and manage all your events in one place.
          </p>
        </div>

        <Link
          to="/operations/events/new"
          className="inline-flex items-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#315A39] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#58761B]"
        >
          <Plus size={18} />
          Create event
        </Link>
      </div>

      {(notice || creationNotice) && (
        <div
          role="status"
          className="flex items-start gap-3 rounded-xl border border-[#B9E6C2] bg-[#F0FFF3] p-4 text-sm font-medium text-[#246336]"
        >
          <CheckCircle2 size={19} className="shrink-0" />
          <span>{notice || creationNotice}</span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
        >
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Total events"
          value={counts.total}
          icon={CalendarDays}
          accent="bg-[#EEF3E8] text-[#58761B]"
        />

        <StatCard
          label="Published"
          value={counts.published}
          icon={CheckCircle2}
          accent="bg-[#E8F6E9] text-[#356B35]"
        />

        <StatCard
          label="Drafts"
          value={counts.draft}
          icon={FilePenLine}
          accent="bg-[#FFF3DD] text-[#B77A00]"
        />
      </div>

      <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-7">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-[#1A3F22]">
              Your events
            </h2>

            <p className="mt-1 text-sm text-[#647064]">
              {visibleEvents.length} event
              {visibleEvents.length === 1 ? '' : 's'} shown
            </p>
          </div>

          <div className="relative w-full sm:w-72">
            <Search
              size={18}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#849382]"
            />

            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search your events"
              aria-label="Search your events"
              className="w-full rounded-xl border border-border-soft bg-white py-3 pl-10 pr-4 text-sm text-[#1A3F22] outline-none transition focus:border-[#58761B] focus:ring-2 focus:ring-[#58761B]/15"
            />
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-2 border-b border-[#E8EDE5] pb-5">
          {[
            ['all', 'All events'],
            ['published', 'Published'],
            ['draft', 'Drafts'],
            ['completed', 'Completed'],
            ['cancelled', 'Cancelled'],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setFilter(value)}
              aria-pressed={filter === value}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                filter === value
                  ? 'bg-[#1A3F22] text-white'
                  : 'bg-[#F4F7F1] text-[#647064] hover:bg-[#E8EFE3]'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="py-16 text-center">
            <LoadingRow label="Loading your events..." />
          </div>
        ) : visibleEvents.length === 0 ? (
          <div className="flex flex-col items-center py-16 text-center">
            <div className="rounded-2xl bg-[#F0F4E9] p-4 text-[#58761B]">
              <CalendarDays size={30} />
            </div>

            <h3 className="mt-5 text-xl font-bold text-[#1A3F22]">
              {events.length === 0
                ? 'Your events will appear here'
                : 'No matching events'}
            </h3>

            <p className="mt-2 max-w-sm text-sm leading-6 text-[#647064]">
              {events.length === 0
                ? 'Create your first event to start organizing with Tuviora.'
                : 'Try a different search or select another status filter.'}
            </p>

            {events.length === 0 && (
              <Link
                to="/operations/events/new"
                className="mt-6 inline-flex items-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3 text-sm font-semibold text-white"
              >
                <Plus size={18} />
                Create your first event
              </Link>
            )}
          </div>
        ) : (
          <div className="mt-7 grid gap-5 lg:grid-cols-2">
            {visibleEvents.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                onPublish={openPublishModal}
                publishingId={publishingId}
                onView={setSelectedEvent}
              />
            ))}
          </div>
        )}
      </section>

      <EventDetailsModal
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        onPublish={openPublishModal}
        publishingId={publishingId}
      />

      <PublishModal
        event={eventToPublish}
        onCancel={closePublishModal}
        onConfirm={confirmPublish}
        publishing={publishingId !== null}
      />
    </div>
  )
}
