import { useEffect, useState } from 'react'
import { Star } from 'lucide-react'
import { getMyFeedback, submitFeedback } from '../lib/feedback'
import { formatApiError } from '../lib/events'

export default function FeedbackForm({ eventId }) {
  const [rating, setRating] = useState(null)
  const [comment, setComment] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    getMyFeedback(eventId)
      .then((data) => {
        if (!active) return
        setRating(data.rating)
        setComment(data.comment || '')
      })
      .catch(() => {}) // 404: no feedback yet
    return () => { active = false }
  }, [eventId])

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      await submitFeedback(eventId, { rating, comment: comment.trim() })
      setMessage('Thanks — your feedback was saved.')
    } catch (err) {
      setMessage(formatApiError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-6 border-t border-border-soft pt-5">
      <p className="text-sm font-semibold">Rate this event</p>
      <div className="mt-2 flex gap-1" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={rating === value}
            aria-label={`${value} star${value > 1 ? 's' : ''}`}
            onClick={() => setRating(value)}
            className="rounded-lg p-1"
          >
            <Star
              size={24}
              className={rating >= value ? 'fill-[#58761B] text-[#58761B]' : 'text-[#B7C2B4]'}
            />
          </button>
        ))}
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={2}
        aria-label="Feedback comment"
        placeholder="What went well? What could be better?"
        className="mt-3 w-full rounded-xl border border-border-soft px-4 py-3 text-sm outline-none focus:border-[#58761B]"
      />
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={saving || (rating === null && !comment.trim())}
          className="rounded-xl bg-[#58761B] px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Submit feedback'}
        </button>
        {message && <p role="status" className="text-sm text-text-muted">{message}</p>}
      </div>
    </form>
  )
}
