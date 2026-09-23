import { CalendarDays, Plus, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function MyEvents() {
  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-5">
        <div>
          <p className="mb-2 font-semibold text-[#58761B]">
            Organizer Workspace
          </p>
          <h1 className="text-3xl font-bold sm:text-4xl">
            My Events
          </h1>
          <p className="mt-3 text-[#647064]">
            Create, organize and manage all your events in one place.
          </p>
        </div>

        <Link
          to="/operations/events/new"
          className="inline-flex items-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3 font-semibold text-white transition-colors hover:bg-[#31563A]"
        >
          <Plus size={19} />
          Create Event
        </Link>
      </div>

      <section className="rounded-2xl border border-[#E3E9DF] bg-white px-6 py-16 text-center sm:px-10">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-2xl bg-[#EDF3E8] text-[#58761B]">
          <CalendarDays size={36} />
        </div>

        <h2 className="mt-7 text-2xl font-bold">
          Your events will appear here
        </h2>

        <p className="mx-auto mt-3 max-w-md leading-7 text-[#647064]">
          Start by creating your first event. You'll be able to manage
          its registration, readiness, communications and more
          from your organizer workspace.
        </p>

        <Link
          to="/operations/events/new"
          className="mt-8 inline-flex items-center gap-2 rounded-xl bg-[#1A3F22] px-6 py-3 font-semibold text-white transition-colors hover:bg-[#31563A]"
        >
          Create your first event
          <ArrowRight size={18} />
        </Link>
      </section>
    </div>
  )
}
