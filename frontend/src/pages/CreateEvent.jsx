import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, CalendarDays, Info } from 'lucide-react'

const initialForm = {
  name: '',
  category: '',
  description: '',
  date: '',
  startTime: '',
  endTime: '',
  venue: '',
  capacity: '',
}

const fieldClass =
  'mt-2 w-full rounded-xl border border-[#DCE5D8] bg-white px-4 py-3 text-[#1A3F22] outline-none transition focus:border-[#58761B] focus:ring-2 focus:ring-[#58761B]/20'

export default function CreateEvent() {
  const [form, setForm] = useState(initialForm)

  function updateField(event) {
    const { name, value } = event.target
    setForm((previous) => ({ ...previous, [name]: value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    // The shared Event API is not implemented yet.
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <div>
        <Link
          to="/operations/events"
          className="inline-flex items-center gap-2 text-sm font-semibold text-[#58761B] hover:text-[#1A3F22]"
        >
          <ArrowLeft size={17} />
          Back to My Events
        </Link>

        <div className="mt-6">
          <p className="font-semibold text-[#58761B]">
            Organizer Workspace
          </p>
          <h1 className="mt-2 text-3xl font-bold sm:text-4xl">
            Create an event
          </h1>
          <p className="mt-3 text-[#647064]">
            Tell us about your event. Start with the essentials,
            then manage the details from your workspace.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="rounded-2xl border border-[#E3E9DF] bg-white p-6 sm:p-8">
          <div className="mb-7 flex items-center gap-3">
            <span className="rounded-xl bg-[#EDF3E8] p-3 text-[#58761B]">
              <CalendarDays size={23} />
            </span>
            <div>
              <h2 className="text-xl font-bold">Event details</h2>
              <p className="text-sm text-[#647064]">
                The basic information about your event.
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <label htmlFor="name" className="font-semibold">
                Event name *
              </label>
              <input
                id="name"
                name="name"
                value={form.name}
                onChange={updateField}
                placeholder="e.g. Kampala Innovation Summit"
                required
                className={fieldClass}
              />
            </div>

            <div>
              <label htmlFor="category" className="font-semibold">
                Event category *
              </label>
              <select
                id="category"
                name="category"
                value={form.category}
                onChange={updateField}
                required
                className={fieldClass}
              >
                <option value="">Select a category</option>
                <option value="conference">Conference</option>
                <option value="hackathon">Hackathon</option>
                <option value="wedding">Wedding</option>
                <option value="workshop">Workshop or training</option>
                <option value="concert">Concert or festival</option>
                <option value="fundraiser">Fundraiser</option>
                <option value="community">Community event</option>
                <option value="corporate">Corporate event</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label htmlFor="description" className="font-semibold">
                Description
              </label>
              <textarea
                id="description"
                name="description"
                value={form.description}
                onChange={updateField}
                rows={4}
                placeholder="What is your event about?"
                className={fieldClass}
              />
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-[#E3E9DF] bg-white p-6 sm:p-8">
          <h2 className="text-xl font-bold">Date and location</h2>
          <p className="mt-2 text-sm text-[#647064]">
            When and where will your event take place?
          </p>

          <div className="mt-7 grid gap-6 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor="date" className="font-semibold">
                Event date *
              </label>
              <input
                id="date"
                name="date"
                type="date"
                value={form.date}
                onChange={updateField}
                required
                className={fieldClass}
              />
            </div>

            <div>
              <label htmlFor="startTime" className="font-semibold">
                Start time *
              </label>
              <input
                id="startTime"
                name="startTime"
                type="time"
                value={form.startTime}
                onChange={updateField}
                required
                className={fieldClass}
              />
            </div>

            <div>
              <label htmlFor="endTime" className="font-semibold">
                End time *
              </label>
              <input
                id="endTime"
                name="endTime"
                type="time"
                value={form.endTime}
                min={form.startTime || undefined}
                onChange={updateField}
                required
                className={fieldClass}
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="venue" className="font-semibold">
                Venue or location *
              </label>
              <input
                id="venue"
                name="venue"
                value={form.venue}
                onChange={updateField}
                placeholder="e.g. National ICT Innovation Hub, Kampala"
                required
                className={fieldClass}
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="capacity" className="font-semibold">
                Expected capacity
              </label>
              <input
                id="capacity"
                name="capacity"
                type="number"
                min="1"
                step="1"
                value={form.capacity}
                onChange={updateField}
                placeholder="e.g. 200"
                className={fieldClass}
              />
            </div>
          </div>
        </section>

        <div className="flex items-start gap-3 rounded-xl border border-[#E8E1C7] bg-[#FFFCF1] p-5 text-sm text-[#715B20]">
          <Info size={20} className="mt-0.5 shrink-0" />
          <p>
            This form is a frontend preview. Event saving will be
            enabled when the shared backend API is connected.
          </p>
        </div>

        <div className="flex flex-wrap justify-end gap-3">
          <Link
            to="/operations/events"
            className="rounded-xl border border-[#DCE5D8] bg-white px-6 py-3 font-semibold text-[#1A3F22] hover:bg-[#F2F6EF]"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled
            title="Event saving is awaiting backend integration"
            className="cursor-not-allowed rounded-xl bg-[#1A3F22] px-6 py-3 font-semibold text-white opacity-50"
          >
            Create Event
          </button>
        </div>
      </form>
    </div>
  )
}
