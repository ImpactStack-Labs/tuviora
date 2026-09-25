import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ScanLine, Star, UserCheck, Users } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import StatCard from '../components/StatCard'
import LoadingRow from '../components/LoadingRow'
import { formatApiError } from '../lib/events'
import { getEventSummary } from '../lib/finance'

const GREEN = '#58761B'

function ChartCard({ title, children, empty }) {
  return (
    <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      {empty
        ? <p className="mt-4 text-sm text-text-muted">No data yet.</p>
        : <div className="mt-4 h-64">{children}</div>}
    </section>
  )
}

export default function AnalyticsPage() {
  const [event, setEvent] = useState(null)
  const [summary, setSummary] = useState(null)
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

    getEventSummary(event.id)
      .then((s) => { if (active) setSummary(s) })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event])

  const regs = summary?.registrations
  const total = regs ? regs.confirmed + regs.payment_pending + regs.cancelled : 0

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Event performance
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Analytics
        </h1>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <EventPicker id="analytics-event" value={event} onChange={setEvent} onError={setError} />

      {loading && <LoadingRow />}

      {summary && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Registrations" value={total} icon={Users} caption={`${regs.cancelled} cancelled`} />
            <StatCard label="Confirmed" value={regs.confirmed} icon={UserCheck} caption={`${regs.payment_pending} awaiting payment`} />
            <StatCard label="Check-in rate" value={`${Math.round(summary.attendance.rate * 100)}%`} icon={ScanLine} caption={`${summary.attendance.checked_in} of ${summary.attendance.confirmed} checked in`} />
            <StatCard label="Average rating" value={summary.feedback.average_rating ?? '—'} icon={Star} caption={`${summary.feedback.count} responses`} />
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <ChartCard title="Registrations per day" empty={!regs.by_day.length}>
              <ResponsiveContainer>
                <LineChart data={regs.by_day}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EDF1EA" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke={GREEN} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Registrations by ticket type" empty={!regs.by_ticket_type.length}>
              <ResponsiveContainer>
                <BarChart data={regs.by_ticket_type}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EDF1EA" />
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="count" fill={GREEN} radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      )}
    </div>
  )
}
