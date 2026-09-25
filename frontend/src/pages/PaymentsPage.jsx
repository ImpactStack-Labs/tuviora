import { useEffect, useState } from 'react'
import { AlertCircle, CircleDollarSign, Clock } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import StatCard from '../components/StatCard'
import LoadingRow from '../components/LoadingRow'
import { formatApiError } from '../lib/events'
import { formatDateTime } from '../lib/format'
import { formatMoney, getEventPayments, getEventSummary } from '../lib/finance'

const STATUSES = ['all', 'completed', 'pending', 'processing', 'failed', 'cancelled']

export default function PaymentsPage() {
  const [event, setEvent] = useState(null)
  const [summary, setSummary] = useState(null)
  const [payments, setPayments] = useState([])
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!event) return
    let active = true
    // Same pattern as sibling pages (e.g. Communications); a loading flag
    // set at the start of a data-fetch effect, not a state sync.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)
    setError('')

    Promise.all([getEventSummary(event.id), getEventPayments(event.id)])
      .then(([s, p]) => {
        if (!active) return
        setSummary(s)
        setPayments(p)
      })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event])

  const shown = filter === 'all' ? payments : payments.filter((p) => p.status === filter)

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Ticket revenue
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Payments
        </h1>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <EventPicker id="payments-event" value={event} onChange={setEvent} onError={setError} />

      {loading && <LoadingRow />}

      {summary && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard label="Collected" value={formatMoney(summary.payments.collected, summary.currency)} icon={CircleDollarSign} />
            <StatCard label="Pending" value={formatMoney(summary.payments.pending, summary.currency)} icon={Clock} caption={`${summary.registrations.payment_pending} registrations awaiting payment`} />
            <StatCard label="Failed payments" value={summary.payments.failed_count} icon={AlertCircle} accent="bg-red-50 text-red-700" />
          </div>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Transactions</h2>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                aria-label="Filter by status"
                className="rounded-xl border border-border-soft bg-white px-3 py-2 text-sm"
              >
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            {!shown.length && <p className="mt-4 text-sm text-text-muted">No payments.</p>}
            {shown.length > 0 && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-text-muted">
                    <tr>
                      <th className="py-2 pr-4">Attendee</th>
                      <th className="py-2 pr-4">Amount</th>
                      <th className="py-2 pr-4">Method</th>
                      <th className="py-2 pr-4">Status</th>
                      <th className="py-2">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EDF1EA]">
                    {shown.map((p) => (
                      <tr key={p.id}>
                        <td className="py-2 pr-4">{p.attendee}</td>
                        <td className="py-2 pr-4">{formatMoney(p.amount, p.currency)}</td>
                        <td className="py-2 pr-4">{p.method.replace('_', ' ')}</td>
                        <td className="py-2 pr-4">{p.status}</td>
                        <td className="py-2">{formatDateTime(p.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
