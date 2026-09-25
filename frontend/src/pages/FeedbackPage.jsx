import { useEffect, useState } from 'react'
import { MessageSquare, Sparkles, Star } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import StatCard from '../components/StatCard'
import LoadingRow from '../components/LoadingRow'
import { formatApiError } from '../lib/events'
import { formatDateTime } from '../lib/format'
import {
  generateFeedbackAnalysis,
  getEventFeedback,
  getFeedbackAnalysis,
} from '../lib/feedback'

export default function FeedbackPage() {
  const [event, setEvent] = useState(null)
  const [feedback, setFeedback] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!event) return
    let active = true
    // Same pattern as sibling pages (e.g. Communications); a loading flag
    // set at the start of a data-fetch effect, not a state sync.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setAnalysis(null)

    Promise.all([
      getEventFeedback(event.id),
      getFeedbackAnalysis(event.id).catch(() => null), // 404: none yet
    ])
      .then(([items, existing]) => {
        if (!active) return
        setFeedback(items)
        setAnalysis(existing)
      })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event])

  async function handleAnalyze() {
    setAnalyzing(true)
    setError('')
    try {
      setAnalysis(await generateFeedbackAnalysis(event.id))
    } catch (err) {
      setError(
        err.status === 503
          ? 'AI summary unavailable — OPENAI_API_KEY is not configured.'
          : formatApiError(err),
      )
    } finally {
      setAnalyzing(false)
    }
  }

  const rated = feedback.filter((f) => f.rating)
  const average = rated.length
    ? (rated.reduce((sum, f) => sum + f.rating, 0) / rated.length).toFixed(1)
    : '—'
  const breakdown = [5, 4, 3, 2, 1].map((star) => ({
    star,
    count: rated.filter((f) => f.rating === star).length,
  }))

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Attendee voice
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Feedback
        </h1>
        <p className="mt-3 max-w-2xl text-text-muted">
          Ratings and comments from attendees on the web and USSD.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <EventPicker id="feedback-event" value={event} onChange={setEvent} onError={setError} />

      {loading && <LoadingRow />}

      {event && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <StatCard label="Average rating" value={average} icon={Star} caption="out of 5" />
            <StatCard label="Responses" value={feedback.length} icon={MessageSquare} />
          </div>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-semibold">Rating breakdown</h2>
            <div className="mt-4 space-y-2">
              {breakdown.map(({ star, count }) => (
                <div key={star} className="flex items-center gap-3 text-sm">
                  <span className="w-10">{star} ★</span>
                  <div className="h-2 flex-1 rounded-full bg-[#EDF1EA]">
                    <div
                      className="h-2 rounded-full bg-[#58761B]"
                      style={{ width: rated.length ? `${(count / rated.length) * 100}%` : 0 }}
                    />
                  </div>
                  <span className="w-8 text-right text-text-muted">{count}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">AI summary</h2>
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={analyzing || !feedback.length}
                className="inline-flex items-center gap-2 rounded-xl bg-[#58761B] px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
              >
                <Sparkles size={16} /> {analyzing ? 'Analysing...' : 'Generate AI summary'}
              </button>
            </div>
            {!analysis && (
              <p className="mt-3 text-sm text-text-muted">No summary generated yet.</p>
            )}
            {analysis && (
              <div className="mt-4 space-y-4 text-sm">
                {analysis.message && <p className="text-text-muted">{analysis.message}</p>}
                {analysis.concerns_summary && <p>{analysis.concerns_summary}</p>}
                {analysis.themes?.length > 0 && (
                  <ul className="space-y-2">
                    {analysis.themes.map((t, i) => (
                      <li key={i}>
                        <span className="font-semibold">{t.theme ?? String(t)}</span>
                        {t.description && ` — ${t.description}`}
                      </li>
                    ))}
                  </ul>
                )}
                {analysis.suggested_improvements?.length > 0 && (
                  <div>
                    <p className="font-semibold">Suggested improvements</p>
                    <ul className="mt-1 list-disc pl-5">
                      {analysis.suggested_improvements.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-semibold">Comments</h2>
            {!feedback.length && (
              <p className="mt-3 text-sm text-text-muted">No feedback yet.</p>
            )}
            <ul className="mt-3 divide-y divide-[#EDF1EA]">
              {feedback.map((f) => (
                <li key={f.id} className="py-3 text-sm">
                  <p className="text-text-muted">
                    {f.rating ? `${f.rating} ★ · ` : ''}{formatDateTime(f.created_at)}
                  </p>
                  {f.comment && <p className="mt-1">{f.comment}</p>}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  )
}
