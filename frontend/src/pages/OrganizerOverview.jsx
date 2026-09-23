import { Link } from 'react-router-dom'
import {
  CalendarDays,
  Users,
  ScanLine,
  Radio,
  ClipboardCheck,
  ArrowRight,
} from 'lucide-react'

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
          <div
            key={name}
            className="rounded-2xl border border-[#E3E9DF] bg-white p-6"
          >
            <div className="flex items-start justify-between">
              <p className="text-[#647064]">{name}</p>
              <span className="rounded-xl bg-[#EDF3E8] p-3 text-[#58761B]">
                <Icon size={22} />
              </span>
            </div>
            <p className="mt-5 text-4xl font-bold">0</p>
            <p className="mt-2 text-sm text-[#7B867B]">
              Awaiting real event data
            </p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-2xl border border-[#E3E9DF] bg-white p-8">
          <h2 className="text-xl font-bold">Upcoming events</h2>
          <div className="flex min-h-56 flex-col items-center justify-center text-center">
            <CalendarDays size={36} className="text-[#58761B]" />
            <h3 className="mt-5 font-bold">No events to display yet</h3>
            <p className="mt-2 text-[#647064]">
              Your upcoming events will appear here.
            </p>
          </div>
        </section>

        <section className="rounded-2xl border border-[#E3E9DF] bg-white p-8">
          <h2 className="text-xl font-bold">Needs your attention</h2>
          <div className="flex min-h-56 flex-col items-center justify-center text-center">
            <ClipboardCheck size={36} className="text-[#58761B]" />
            <h3 className="mt-5 font-bold">Nothing to review yet</h3>
            <p className="mt-2 text-[#647064]">
              Tasks and incidents will appear here.
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}
