import { useEffect, useState } from 'react'
import { getLeadEvents, formatApiError } from '../lib/events'

export default function EventPicker({ id, value, onChange, onError }) {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    getLeadEvents()
      .then((data) => {
        if (!active) return
        const list = Array.isArray(data) ? data : data.results || []
        setEvents(list)
        if (list.length) onChange(list[0])
      })
      .catch((err) => {
        if (active) onError?.(formatApiError(err))
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
    // Load once; parents pass inline callbacks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
      <label htmlFor={id} className="mb-2 block text-sm font-semibold">
        Select an event
      </label>
      <select
        id={id}
        value={value ? String(value.id) : ''}
        onChange={(e) =>
          onChange(events.find((ev) => String(ev.id) === e.target.value))
        }
        disabled={loading || !events.length}
        className="w-full rounded-xl border border-border-soft bg-white px-4 py-3 outline-none focus:border-[#58761B] sm:max-w-xl"
      >
        {!events.length && (
          <option value="">{loading ? 'Loading events…' : 'No events available'}</option>
        )}
        {events.map((ev) => (
          <option key={ev.id} value={String(ev.id)}>
            {ev.name}
          </option>
        ))}
      </select>
      {value && (
        <p className="mt-3 text-sm text-text-muted">
          {value.category} · {value.date}
        </p>
      )}
    </section>
  )
}
