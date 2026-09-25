import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Clock3,
  MapPin,
  Search,
  Users,
} from 'lucide-react'
import { formatEventDate, formatEventTime } from '../lib/format'
import EmptyState from '../components/EmptyState'
import LoadingRow from '../components/LoadingRow'

const categoryLabels = {
  conference: 'Conference',
  hackathon: 'Hackathon',
  workshop: 'Workshop',
  wedding: 'Wedding',
  concert: 'Concert',
  fundraiser: 'Fundraiser',
  community: 'Community',
  corporate: 'Corporate',
  other: 'Other',
}

export default function PublicEvents() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadEvents() {
      setLoading(true)
      setError('')

      try {
        const response = await fetch('/api/events/public/', {
          signal: controller.signal,
          headers: { Accept: 'application/json' },
        })

        if (!response.ok) {
          throw new Error('Unable to load events. Please try again.')
        }

        const data = await response.json()
        setEvents(Array.isArray(data) ? data : data.results || [])
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

    loadEvents()
    return () => controller.abort()
  }, [reload])

  const categories = useMemo(
    () => [...new Set(events.map((event) => event.category))],
    [events],
  )

  const visibleEvents = useMemo(() => {
    const term = search.trim().toLowerCase()

    return events.filter((event) => {
      const matchesCategory =
        category === 'all' || event.category === category
      const matchesSearch =
        !term ||
        [event.name, event.description, event.venue, event.category]
          .some((value) => String(value || '').toLowerCase().includes(term))

      return matchesCategory && matchesSearch
    })
  }, [events, search, category])

  return (
    <div className="min-h-screen bg-[#F7F9F5] text-[#1A3F22]">
      <header className="border-b border-border-soft bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-5 lg:px-8">
          <Link to="/" className="text-2xl font-bold tracking-tight">
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
              to="/"
              className="inline-flex items-center gap-2 text-sm font-semibold text-[#58761B] hover:underline"
            >
              <ArrowLeft size={17} />
              Back to home
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="bg-[#1A3F22] px-5 py-16 text-white sm:py-20">
          <div className="mx-auto max-w-7xl lg:px-3">
            <p className="text-sm font-bold uppercase tracking-[.18em] text-[#E9B64E]">
              Discover events
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">
              Find your next experience.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-white/80">
              Explore upcoming events and find something worth being part of.
            </p>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-5 py-12 lg:px-8">
          <div className="mb-9 flex flex-col gap-4 sm:flex-row">
            <label className="relative flex-1">
              <span className="sr-only">Search events</span>
              <Search
                size={20}
                className="absolute left-4 top-3.5 text-[#718072]"
              />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search events or venues"
                className="w-full rounded-xl border border-border-soft bg-white py-3 pl-12 pr-4 outline-none focus:border-[#58761B]"
              />
            </label>

            <label>
              <span className="sr-only">Filter by category</span>
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="w-full rounded-xl border border-border-soft bg-white px-4 py-3 outline-none focus:border-[#58761B] sm:w-56"
              >
                <option value="all">All categories</option>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {categoryLabels[item] || item}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {loading ? (
            <div className="py-20 text-center">
              <LoadingRow label="Loading upcoming events..." />
            </div>
          ) : error ? (
            <div role="alert" className="rounded-2xl border border-red-200 bg-white p-10 text-center">
              <p className="text-red-700">{error}</p>
              <button
                onClick={() => setReload((value) => value + 1)}
                className="mt-5 rounded-lg bg-[#1A3F22] px-5 py-3 font-semibold text-white"
              >
                Try again
              </button>
            </div>
          ) : visibleEvents.length === 0 ? (
            <EmptyState
              as="h2"
              size="lg"
              icon={CalendarDays}
              title={events.length ? 'No matching events' : 'No upcoming events yet'}
              description={
                events.length
                  ? 'Try a different search or category.'
                  : 'Check back soon for new events.'
              }
            />
          ) : (
            <>
              <p className="mb-6 text-sm font-medium text-[#647064]">
                {visibleEvents.length} upcoming {visibleEvents.length === 1 ? 'event' : 'events'}
              </p>
              <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                {visibleEvents.map((event) => (
                  <article
                    key={event.id}
                    className="flex flex-col overflow-hidden rounded-2xl border border-border-soft bg-white shadow-sm"
                  >
                    <div className="bg-[#EDF3E8] px-6 py-7">
                      <span className="inline-flex rounded-full bg-white px-3 py-1 text-xs font-bold text-[#58761B]">
                        {categoryLabels[event.category] || event.category}
                      </span>
                      <h2 className="mt-5 text-2xl font-bold">
                        {event.name}
                      </h2>
                    </div>

                    <div className="flex flex-1 flex-col p-6">
                      <p className="mb-6 line-clamp-3 text-sm leading-7 text-[#647064]">
                        {event.description || 'Join us for this upcoming event.'}
                      </p>

                      <div className="space-y-3 text-sm text-[#405642]">
                        <p className="flex items-center gap-3">
                          <CalendarDays size={18} className="shrink-0 text-[#58761B]" />
                          {formatEventDate(event.date)}
                        </p>
                        <p className="flex items-center gap-3">
                          <Clock3 size={18} className="shrink-0 text-[#58761B]" />
                          {formatEventTime(event.start_time)} – {formatEventTime(event.end_time)}
                        </p>
                        <p className="flex items-center gap-3">
                          <MapPin size={18} className="shrink-0 text-[#58761B]" />
                          {event.event_format === 'virtual'
                            ? 'Virtual event'
                            : event.venue || 'Venue to be announced'}
                        </p>
                        {event.capacity && (
                          <p className="flex items-center gap-3">
                            <Users size={18} className="shrink-0 text-[#58761B]" />
                            Capacity: {event.capacity}
                          </p>
                        )}
                      </div>

                      <div className="mt-7 border-t border-border-soft pt-5">
                        <Link
                          to={`/events/${event.id}`}
                          className="flex items-center gap-2 text-sm font-semibold text-[#58761B] hover:underline"
                        >
                          View event and register
                          <ArrowRight size={17} />
                        </Link>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  )
}
