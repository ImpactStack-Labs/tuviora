import { useEffect, useState } from 'react'
import { BellRing, Send } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import LoadingRow from '../components/LoadingRow'
import { getAnnouncements, sendAnnouncement } from '../lib/announcements'
import { formatApiError } from '../lib/events'
import { formatDateTime, formatEventDate } from '../lib/format'

const MAX_LENGTH = 480

function smsSegments(text) {
  if (!text.length) return 0
  return text.length <= 160 ? 1 : Math.ceil(text.length / 153)
}

function reminderTemplate(event) {
  return (
    `Reminder: ${event.name} is on ${formatEventDate(event.date)} ` +
    `at ${String(event.start_time).slice(0, 5)}, ${event.venue || 'online'}.`
  )
}

export default function Communications() {
  const [event, setEvent] = useState(null)
  const [announcements, setAnnouncements] = useState([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (!event) return
    let active = true
    // Same pattern as sibling pages (e.g. EventReadiness); a loading flag
    // set at the start of a data-fetch effect, not a state sync.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)

    getAnnouncements(event.id)
      .then((data) => { if (active) setAnnouncements(data) })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event, refreshKey])

  async function handleSend(e) {
    e.preventDefault()
    if (!event || sending || !message.trim()) return
    if (!window.confirm('Send this SMS to all confirmed attendees?')) return

    setSending(true)
    setError('')
    setNotice('')

    try {
      const result = await sendAnnouncement(event.id, message.trim())
      setMessage('')
      setNotice(
        `Sent to ${result.submitted} · ${result.skipped} skipped ` +
        `(no SMS consent or phone) · ${result.failed} failed.`,
      )
      setRefreshKey((k) => k + 1)
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Attendee communication
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Communications
        </h1>
        <p className="mt-3 max-w-2xl text-text-muted">
          Send SMS announcements and reminders to confirmed attendees who
          opted in to SMS.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}
      {notice && (
        <div role="status" className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          {notice}
        </div>
      )}

      <EventPicker
        id="communications-event"
        value={event}
        onChange={(ev) => { setEvent(ev); setNotice(''); setError('') }}
        onError={setError}
      />

      <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-[#1A3F22]">New announcement</h2>
          <button
            type="button"
            disabled={!event}
            onClick={() => setMessage(reminderTemplate(event))}
            className="inline-flex items-center gap-2 rounded-xl border border-border-soft bg-white px-4 py-2 text-sm font-semibold disabled:opacity-50"
          >
            <BellRing size={16} /> Insert reminder
          </button>
        </div>
        <form onSubmit={handleSend} className="mt-4 space-y-3">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            maxLength={MAX_LENGTH}
            rows={4}
            aria-label="Announcement message"
            placeholder="e.g. Doors open at 8am. Bring your ticket QR code."
            className="w-full rounded-xl border border-border-soft bg-white px-4 py-3 focus:border-[#58761B]"
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-text-muted">
              {message.length}/{MAX_LENGTH} characters · {smsSegments(message)} SMS
            </p>
            <button
              type="submit"
              disabled={!event || sending || !message.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-[#58761B] px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
            >
              <Send size={16} /> {sending ? 'Sending...' : 'Send to attendees'}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
        <h2 className="text-xl font-bold">History</h2>
        {loading && <LoadingRow className="mt-4" />}
        {!loading && !announcements.length && (
          <p className="mt-4 text-sm text-text-muted">No announcements sent yet.</p>
        )}
        <ul className="mt-4 divide-y divide-[#EDF1EA]">
          {announcements.map((a) => (
            <li key={a.id} className="py-4">
              <p className="text-sm text-text-muted">
                {formatDateTime(a.created_at)} · {a.sent_by_name || 'Automatic reminder'}
              </p>
              <p className="mt-1">{a.message}</p>
              <p className="mt-1 text-sm text-text-muted">
                {a.submitted} sent · {a.skipped} skipped · {a.failed} failed
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
