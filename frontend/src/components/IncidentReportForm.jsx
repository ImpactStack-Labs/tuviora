import { useState } from 'react'
import { apiRequest } from '../lib/auth'

const CATEGORIES = [
  'network', 'power', 'venue', 'security',
  'attendance', 'payment', 'technical', 'other',
]

// Shared by the organizer's Incident Management page and the Team Workspace.
export default function IncidentReportForm({ eventId, onCreated, onError }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('other')
  const [severity, setSeverity] = useState('medium')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!eventId || submitting) return

    setSubmitting(true)
    onError('')

    try {
      const created = await apiRequest(`/api/events/${eventId}/incidents/`, {
        method: 'POST',
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          category,
          severity,
        }),
      })

      setTitle('')
      setDescription('')
      setCategory('other')
      setSeverity('medium')
      onCreated(created)
    } catch (err) {
      onError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-6 grid gap-4">
      <label className="grid gap-2 text-sm font-semibold">
        What happened?
        <input
          required
          maxLength={255}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="e.g. Registration desk needs assistance"
          className="rounded-xl border border-[#DDE6D6] p-3"
        />
      </label>

      <label className="grid gap-2 text-sm font-semibold">
        Description
        <textarea
          required
          rows={4}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Describe the problem and the help needed."
          className="rounded-xl border border-[#DDE6D6] p-3"
        />
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-2 text-sm font-semibold">
          Category
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="rounded-xl border border-[#DDE6D6] p-3"
          >
            {CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {value.charAt(0).toUpperCase() + value.slice(1)}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-2 text-sm font-semibold">
          Urgency
          <select
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
            className="rounded-xl border border-[#DDE6D6] p-3"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </label>
      </div>

      <button
        type="submit"
        disabled={!eventId || submitting}
        className="rounded-xl bg-[#1A3F22] px-5 py-3 font-semibold text-white disabled:opacity-50 sm:justify-self-start"
      >
        {submitting ? 'Submitting...' : 'Submit report'}
      </button>
    </form>
  )
}
