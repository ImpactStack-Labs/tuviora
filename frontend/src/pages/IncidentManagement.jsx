import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { apiRequest } from '../lib/auth'
import { getEvents } from '../lib/events'

const STATUSES = [
  ['open', 'Open'],
  ['in_progress', 'In progress'],
  ['resolved', 'Resolved'],
  ['closed', 'Closed'],
]

export default function IncidentManagement() {
  const [events, setEvents] = useState([])
  const [eventId, setEventId] = useState('')
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [savingId, setSavingId] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let active = true

    getEvents()
      .then((data) => {
        if (!active) return
        const list = Array.isArray(data)
          ? data
          : data.results || []
        setEvents(list)
        setEventId(list.length ? String(list[0].id) : '')
      })
      .catch((err) => {
        if (active) setError(err.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!eventId) {
      setIncidents([])
      return
    }

    let active = true
    setLoading(true)
    setError('')

    apiRequest(`/api/events/${eventId}/incidents/`)
      .then((data) => {
        if (!active) return
        setIncidents(
          Array.isArray(data) ? data : data.results || []
        )
      })
      .catch((err) => {
        if (active) setError(err.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [eventId, refreshKey])

  async function updateStatus(incident, status) {
    if (savingId !== null) return

    setSavingId(incident.id)
    setError('')
    setNotice('')

    try {
      const updated = await apiRequest(
        `/api/events/${eventId}/incidents/${incident.id}/`,
        {
          method: 'PATCH',
          body: JSON.stringify({ status }),
        },
      )

      setIncidents((current) =>
        current.map((item) =>
          item.id === updated.id ? updated : item
        )
      )
      setNotice('Incident status updated.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingId(null)
    }
  }

  const openCount = incidents.filter(
    (item) => ['open', 'in_progress'].includes(item.status)
  ).length

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-semibold text-[#58761B]">
            Event operations
          </p>
          <h1 className="mt-2 text-3xl font-bold">
            Incident Management
          </h1>
          <p className="mt-2 text-[#647064]">
            Review problems reported by your event team.
          </p>
        </div>

        <button
          type="button"
          disabled={!eventId || loading}
          onClick={() => setRefreshKey((value) => value + 1)}
          className="flex items-center gap-2 rounded-xl border border-[#DDE6D6] bg-white px-4 py-3 font-semibold disabled:opacity-50"
        >
          <RefreshCw size={18} />
          Refresh
        </button>
      </div>

      {error && (
        <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-700">
          {error}
        </p>
      )}

      {notice && (
        <p role="status" className="rounded-xl bg-green-50 p-4 text-green-800">
          {notice}
        </p>
      )}

      <section className="rounded-2xl border border-[#E3E9DF] bg-white p-6">
        <label htmlFor="incident-event" className="block font-semibold">
          Select event
        </label>
        <select
          id="incident-event"
          value={eventId}
          onChange={(event) => setEventId(event.target.value)}
          className="mt-3 w-full rounded-xl border border-[#DDE6D6] p-3 sm:max-w-lg"
        >
          {!events.length && (
            <option value="">No events available</option>
          )}
          {events.map((event) => (
            <option key={event.id} value={String(event.id)}>
              {event.name}
            </option>
          ))}
        </select>

        <div className="mt-6 flex items-center gap-3">
          <AlertTriangle size={22} className="text-[#B7791F]" />
          <p className="text-lg font-bold">
            {openCount} active incident{openCount === 1 ? '' : 's'}
          </p>
        </div>
      </section>

      {loading ? (
        <p className="flex items-center gap-2 text-[#647064]">
          <RefreshCw size={18} className="animate-spin" />
          Loading incidents...
        </p>
      ) : incidents.length === 0 ? (
        <div className="rounded-2xl border border-[#E3E9DF] bg-white p-8 text-center">
          <p className="font-semibold">No incidents reported</p>
          <p className="mt-2 text-sm text-[#647064]">
            Team reports will appear here.
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {incidents.map((incident) => (
            <article
              key={incident.id}
              className="rounded-2xl border border-[#E3E9DF] bg-white p-6"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h2 className="text-xl font-bold">{incident.title}</h2>
                <span className="rounded-full bg-[#FFF3DD] px-3 py-1 text-sm font-semibold text-[#865A17]">
                  {incident.severity} urgency
                </span>
              </div>

              <p className="mt-3 text-[#647064]">
                {incident.description}
              </p>

              <p className="mt-4 text-sm text-[#647064]">
                Category: {incident.category}
                {' · '}
                Status: {incident.status.replaceAll('_', ' ')}
              </p>

              <div className="mt-5 flex flex-wrap gap-2 border-t border-[#EDF0EA] pt-4">
                {STATUSES.map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    disabled={
                      savingId !== null ||
                      incident.status === value
                    }
                    onClick={() => updateStatus(incident, value)}
                    className={`rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50 ${
                      incident.status === value
                        ? 'bg-[#1A3F22] text-white'
                        : 'border border-[#DDE6D6] hover:bg-[#F0F5E9]'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
