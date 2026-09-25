import { Link } from 'react-router-dom'
import {
  CalendarDays,
  Users,
  ScanLine,
  Radio,
  ClipboardCheck,
  ArrowRight,
} from 'lucide-react'
import StatCard from '../components/StatCard'
import EmptyState from '../components/EmptyState'

export default function OrganizerOverview() {
  const stats = [
    { name: 'Your events', icon: CalendarDays },
    { name: 'Registrations', icon: Users },
    { name: 'Checked in', icon: ScanLine },
    { name: 'Open incidents', icon: Radio },
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-5">
        <div>
          <p className="mb-2 font-semibold text-[#58761B]">Overview</p>
          <h1 className="text-3xl font-bold sm:text-4xl">
            Your event workspace
          </h1>
          <p className="mt-3 text-[#647064]">
            Everything you need to keep your events on track.
          </p>
        </div>

        <Link
          to="/operations/events"
          className="inline-flex items-center gap-2 rounded-lg bg-[#1A3F22] px-5 py-3 font-semibold text-white hover:bg-[#31563A]"
        >
          My Events <ArrowRight size={18} />
        </Link>
      </div>

      <p className="rounded-xl border border-[#E8E1C7] bg-[#FFFCF1] px-5 py-4 text-sm text-[#715B20]">
        Foundation preview: These figures are placeholders until we connect
        your event data.
      </p>

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map(({ name, icon: Icon }) => (
          <StatCard
            key={name}
            label={name}
            value="0"
            icon={Icon}
            caption="Awaiting real event data"
          />
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-2xl border border-border-soft bg-white p-8">
          <h2 className="mb-5 text-xl font-bold">Upcoming events</h2>
          <EmptyState
            icon={CalendarDays}
            title="No events to display yet"
            description="Your upcoming events will appear here."
            bordered={false}
          />
        </section>

        <section className="rounded-2xl border border-border-soft bg-white p-8">
          <h2 className="mb-5 text-xl font-bold">Needs your attention</h2>
          <EmptyState
            icon={ClipboardCheck}
            title="Nothing to review yet"
            description="Tasks and incidents will appear here."
            bordered={false}
          />
        </section>
      </div>
    </div>
  )
}
