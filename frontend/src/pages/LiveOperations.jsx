import { useEffect, useState } from 'react'
import {
  Activity,
  AlertCircle,
  CalendarDays,
  PhoneCall,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react'

import { getEvents, formatApiError } from '../lib/events'
import { getConferenceStatus } from '../lib/conference'

const STATUS_LABELS = {
  not_started: 'Not started',
  active: 'Active',
  ended: 'Ended',
}

export default function LiveOperations() {
  const [events, setEvents] = useState([])
  const [selectedEventId, setSelectedEventId] = useState('')
  const [conference, setConference] = useState(null)
  const [loadingEvents, setLoadingEvents] = useState(true)
  const [loadingConference, setLoadingConference] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    getEvents()
      .then((data) => {
        if (!active) return

        const list = Array.isArray(data)
          ? data
          : data.results || []

        setEvents(list)

        if (list.length) {
          setSelectedEventId(String(list[0].id))
        }
      })
      .catch((err) => {
        if (active) setError(formatApiError(err))
      })
      .finally(() => {
        if (active) setLoadingEvents(false)
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!selectedEventId) {
      setConference(null)
      return
    }

    let active = true

    setConference(null)
    setLoadingConference(true)
    setError('')

    getConferenceStatus(selectedEventId)
      .then((data) => {
        if (active) setConference(data)
      })
      .catch((err) => {
        if (active) setError(formatApiError(err))
      })
      .finally(() => {
        if (active) setLoadingConference(false)
      })

    return () => {
      active = false
    }
  }, [selectedEventId, refreshKey])

  const selectedEvent = events.find(
    (event) => String(event.id) === selectedEventId,
  )

  const status = conference?.status || 'not_started'

  return (
    <div className="space-y-7">
      <div>
        <p className="text-sm font-semibold text-[#58761B]">
          Event operations
        </p>

        <h1 className="mt-2 text-3xl font-bold text-[#1A3F22]">
          Live Operations
        </h1>

        <p className="mt-3 max-w-3xl text-[#647064]">
          Monitor your event conference and coordinate your
          event team from one workspace.
        </p>
      </div>

      <div
        className="rounded-xl border border-[#E9D8A6]
          bg-[#FFF9E8] p-5"
      >
        <div className="flex items-start gap-3">
          <AlertCircle
            className="mt-1 shrink-0 text-[#A66A00]"
            size={22}
          />

          <div>
            <h2 className="font-bold text-[#805400]">
              Conference calling is not yet available
            </h2>

            <p className="mt-2 text-sm leading-6 text-[#805400]">
              The conference backend is implemented, but
              incoming-call authentication must be completed
              and verified before live calling is enabled.
            </p>
          </div>
        </div>
      </div>

      <section className="rounded-2xl border border-[#E3E9DF] bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <CalendarDays className="text-[#58761B]" size={22} />

          <h2 className="text-xl font-bold text-[#1A3F22]">
            Select an event
          </h2>
        </div>

        {loadingEvents ? (
          <p className="mt-5 text-[#647064]">
            Loading events...
          </p>
        ) : events.length === 0 ? (
          <p className="mt-5 text-[#647064]">
            No events are available. Create an event first.
          </p>
        ) : (
          <select
            value={selectedEventId}
            onChange={(event) =>
              setSelectedEventId(event.target.value)
            }
            className="mt-5 w-full rounded-xl border
              border-[#DDE6D6] bg-white px-4 py-3
              text-[#1A3F22]"
          >
            {events.map((event) => (
              <option key={event.id} value={event.id}>
                {event.name}
              </option>
            ))}
          </select>
        )}
      </section>

      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-200
            bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
        </div>
      )}

      {selectedEvent && (
        <section className="rounded-2xl border border-[#E3E9DF] bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <PhoneCall className="text-[#58761B]" size={24} />

                <h2 className="text-xl font-bold text-[#1A3F22]">
                  Event conference
                </h2>
              </div>

              <p className="mt-2 text-sm text-[#647064]">
                {selectedEvent.name}
              </p>
            </div>

            <button
              type="button"
              disabled={loadingConference}
              onClick={() =>
                setRefreshKey((value) => value + 1)
              }
              className="inline-flex items-center gap-2
                rounded-lg border border-[#DDE6D6]
                px-4 py-2 text-sm font-semibold
                text-[#1A3F22] disabled:opacity-50"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>

          {loadingConference ? (
            <p className="mt-6 text-[#647064]">
              Loading conference status...
            </p>
          ) : conference ? (
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl bg-[#F7F9F5] p-5">
                <Activity
                  className="text-[#58761B]"
                  size={23}
                />

                <p className="mt-3 text-sm text-[#647064]">
                  Conference status
                </p>

                <p className="mt-1 text-xl font-bold text-[#1A3F22]">
                  {STATUS_LABELS[status] || status}
                </p>
              </div>

              <div className="rounded-xl bg-[#F7F9F5] p-5">
                <ShieldCheck
                  className="text-[#58761B]"
                  size={23}
                />

                <p className="mt-3 text-sm text-[#647064]">
                  Your permissions
                </p>

                <p className="mt-1 text-xl font-bold text-[#1A3F22]">
                  {conference.can_manage
                    ? 'Event organizer'
                    : 'Event team member'}
                </p>
              </div>
            </div>
          ) : null}

          <div className="mt-6 border-t border-[#E3E9DF] pt-5">
            <p className="text-sm text-[#647064]">
              Starting conferences and generating access
              codes will become available after secure
              incoming-call integration is completed.
            </p>

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                disabled
                className="rounded-lg bg-[#1A3F22]
                  px-5 py-3 font-semibold text-white
                  opacity-50"
              >
                Start conference
              </button>

              <button
                type="button"
                disabled
                className="rounded-lg border border-[#DDE6D6]
                  px-5 py-3 font-semibold text-[#1A3F22]
                  opacity-50"
              >
                Generate access code
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
