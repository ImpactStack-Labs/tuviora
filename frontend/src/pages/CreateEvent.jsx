import EventTimezone from '../components/EventTimezone'
import { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createEvent, createTicketType, formatApiError } from '../lib/events'
import { ArrowLeft, CalendarDays, ExternalLink, Info, MapPin } from 'lucide-react'
import VenueMap from '../components/maps/VenueMap'
import VenueSearch from '../components/maps/VenueSearch'

const initialForm = {
  name: '',
  category: '',
  description: '',
  date: '',
  timezone: 'Africa/Kampala',
  startTime: '',
  endTime: '',
  eventFormat: 'physical',
  onlinePlatform: '',
  onlineUrl: '',
  joiningInstructions: '',
  venue: '',
  landmark: '',
  latitude: null,
  longitude: null,
  capacity: '',
  isPaid: false,
  ticketTypes: [{ key: 0, name: '', price: '', currency: 'UGX' }],
}

const fieldClass =
  'mt-2 w-full rounded-xl border border-[#DCE5D8] bg-white px-4 py-3 text-[#1A3F22] outline-none transition focus:border-[#58761B] focus:ring-2 focus:ring-[#58761B]/20'

export default function CreateEvent() {
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const createdEventRef = useRef(null)
  const navigate = useNavigate()
  const hasPhysicalLocation =
    form.eventFormat === 'physical' ||
    form.eventFormat === 'hybrid'

  const hasVirtualLocation =
    form.eventFormat === 'virtual' ||
    form.eventFormat === 'hybrid'


  function updateField(event) {
    const { name, value } = event.target

    setForm((previous) => {
      // Clear old coordinates when the venue details change.
      // This prevents directions pointing to a previous venue.
      if (name === 'venue' || name === 'landmark') {
        return {
          ...previous,
          [name]: value,
          latitude: null,
          longitude: null,
        }
      }

      return {
        ...previous,
        [name]: value,
      }
    })
  }

  function updateLocation({ latitude, longitude }) {
    setForm((previous) => ({
      ...previous,
      latitude,
      longitude,
    }))
  }

  function updateTicketType(key, field, value) {
    setForm((previous) => ({
      ...previous,
      ticketTypes: previous.ticketTypes.map((ticket) =>
        ticket.key === key ? { ...ticket, [field]: value } : ticket,
      ),
    }))
  }

  function addTicketType() {
    setForm((previous) => ({
      ...previous,
      ticketTypes: [
        ...previous.ticketTypes,
        { key: Date.now(), name: '', price: '', currency: 'UGX' },
      ],
    }))
  }

  function removeTicketType(key) {
    setForm((previous) => ({
      ...previous,
      ticketTypes: previous.ticketTypes.filter((t) => t.key !== key),
    }))
  }

  const hasLocation =
    Number.isFinite(form.latitude) &&
    Number.isFinite(form.longitude)

  const directionsUrl = hasLocation
    ? `https://www.google.com/maps/dir/?api=1&destination=${form.latitude}%2C${form.longitude}`
    : null

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    const validTickets = form.isPaid
      ? form.ticketTypes.filter(
          (t) => t.name.trim() && Number(t.price) > 0,
        )
      : []

    if (form.isPaid && !validTickets.length) {
      setError(
        'Add at least one ticket type with a name and a price greater ' +
        'than zero, or turn off "This is a paid event".',
      )
      return
    }

    setSaving(true)

    const physical = ['physical', 'hybrid'].includes(form.eventFormat)
    const virtual = ['virtual', 'hybrid'].includes(form.eventFormat)

    const payload = {
      name: form.name.trim(),
      category: form.category,
      description: form.description.trim(),
      date: form.date,
      timezone_name: form.timezone,
      start_time: form.startTime,
      end_time: form.endTime,
      event_format: form.eventFormat,
      venue: physical ? form.venue.trim() : '',
      landmark: physical ? form.landmark.trim() : '',
      latitude: physical && Number.isFinite(form.latitude)
        ? Number(form.latitude.toFixed(6))
        : null,
      longitude: physical && Number.isFinite(form.longitude)
        ? Number(form.longitude.toFixed(6))
        : null,
      online_platform: virtual ? form.onlinePlatform : '',
      online_url: virtual ? form.onlineUrl.trim() : '',
      joining_instructions: virtual
        ? form.joiningInstructions.trim()
        : '',
      capacity: form.capacity ? Number(form.capacity) : null,
    }

    try {
      let created = createdEventRef.current
      if (!created) {
        created = await createEvent(payload)
        createdEventRef.current = created
      }

      for (const ticket of validTickets) {
        // ponytail: sequential, not Promise.all — keeps ticket type
        // order predictable and errors attributable to one row.
        // Revisit if organizers routinely add >10 tiers.
        await createTicketType(created.id, {
          name: ticket.name.trim(),
          price: Number(ticket.price),
          currency: ticket.currency,
        })
      }

      navigate('/operations/events', {
        state: { message: 'Event created successfully as a draft.' },
      })
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSaving(false)
    }
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
          <div className="mt-5">
            <EventTimezone
              value={form.timezone}
              date={form.date}
              onChange={(timezone) =>
                setForm((previous) => ({
                  ...previous,
                  timezone,
                }))
              }
            />
          </div>
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
              <label htmlFor="eventFormat" className="font-semibold">
                Event format *
              </label>
              <select
                id="eventFormat"
                name="eventFormat"
                value={form.eventFormat}
                onChange={updateField}
                required
                className={fieldClass}
              >
                <option value="physical">Physical event</option>
                <option value="virtual">Virtual event</option>
                <option value="hybrid">Hybrid event</option>
              </select>
              <p className="mt-2 text-sm text-[#647064]">
                Choose whether attendees will join in person,
                online or both.
              </p>
            </div>

            {hasPhysicalLocation && (
              <>
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
              <label htmlFor="landmark" className="font-semibold">
                Nearby landmark
              </label>
              <input
                id="landmark"
                name="landmark"
                value={form.landmark}
                onChange={updateField}
                placeholder="e.g. Opposite the main entrance"
                className={fieldClass}
              />
            </div>

            <div className="sm:col-span-2 space-y-4">
              <div className="flex items-start gap-3">
                <span className="rounded-xl bg-[#EDF3E8] p-3 text-[#58761B]">
                  <MapPin size={22} />
                </span>
                <div>
                  <h3 className="font-bold text-[#1A3F22]">
                    Pin your event venue
                  </h3>
                  <p className="mt-1 text-sm text-[#647064]">
                    Click the map to mark the exact entrance or
                    meeting point. You can zoom and move the map
                    before choosing a location.
                  </p>
                </div>
              </div>

              <VenueSearch
                venue={form.venue}
                landmark={form.landmark}
                onLocationSelect={updateLocation}
              />

              <VenueMap
                latitude={form.latitude}
                longitude={form.longitude}
                onLocationChange={updateLocation}
              />

              {hasLocation && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[#F2F6EF] p-4">
                  <p className="text-sm text-[#1A3F22]">
                    Venue location selected. Check that the pin
                    marks the correct entrance.
                  </p>
                  <a
                    href={directionsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-xl bg-[#1A3F22] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#315C38]"
                  >
                    Preview directions
                    <ExternalLink size={16} />
                  </a>
                </div>
              )}
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
              </>
            )}

            {hasVirtualLocation && (
              <div className="sm:col-span-2 space-y-5 rounded-2xl border border-[#DCE5D8] bg-[#F7FAF5] p-5">
                <div>
                  <h3 className="text-lg font-bold text-[#1A3F22]">
                    Virtual event details
                  </h3>
                  <p className="mt-1 text-sm text-[#647064]">
                    Provide the information attendees need to join online.
                  </p>
                </div>

                <div>
                  <label htmlFor="onlinePlatform" className="font-semibold">
                    Online platform *
                  </label>
                  <select
                    id="onlinePlatform"
                    name="onlinePlatform"
                    value={form.onlinePlatform}
                    onChange={updateField}
                    required={hasVirtualLocation}
                    className={fieldClass}
                  >
                    <option value="">Select a platform</option>
                    <option value="zoom">Zoom</option>
                    <option value="google_meet">Google Meet</option>
                    <option value="microsoft_teams">Microsoft Teams</option>
                    <option value="youtube_live">YouTube Live</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="onlineUrl" className="font-semibold">
                    Meeting or streaming link *
                  </label>
                  <input
                    id="onlineUrl"
                    name="onlineUrl"
                    type="url"
                    value={form.onlineUrl}
                    onChange={updateField}
                    placeholder="https://..."
                    required={hasVirtualLocation}
                    className={fieldClass}
                  />
                </div>

                <div>
                  <label
                    htmlFor="joiningInstructions"
                    className="font-semibold"
                  >
                    Joining instructions
                  </label>
                  <textarea
                    id="joiningInstructions"
                    name="joiningInstructions"
                    value={form.joiningInstructions}
                    onChange={updateField}
                    rows={3}
                    placeholder="Optional joining instructions"
                    className={fieldClass}
                  />
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-[#E3E9DF] bg-white p-6 sm:p-8">
          <h2 className="text-xl font-bold">Tickets &amp; pricing</h2>
          <p className="mt-2 text-sm text-[#647064]">
            Leave this off for a free event. Turn it on to charge
            attendees and offer more than one ticket tier.
          </p>

          <label className="mt-5 flex items-center gap-3">
            <input
              type="checkbox"
              checked={form.isPaid}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  isPaid: event.target.checked,
                }))
              }
            />
            <span className="font-semibold">This is a paid event</span>
          </label>

          {form.isPaid && (
            <div className="mt-6 space-y-4">
              {form.ticketTypes.map((ticket) => (
                <div
                  key={ticket.key}
                  className="grid gap-3 rounded-xl border border-[#DCE5D8] p-4 sm:grid-cols-[2fr_1fr_1fr_auto]"
                >
                  <input
                    value={ticket.name}
                    onChange={(event) =>
                      updateTicketType(ticket.key, 'name', event.target.value)
                    }
                    placeholder="e.g. Standard"
                    className={fieldClass}
                  />
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={ticket.price}
                    onChange={(event) =>
                      updateTicketType(ticket.key, 'price', event.target.value)
                    }
                    placeholder="Price"
                    className={fieldClass}
                  />
                  <select
                    value={ticket.currency}
                    onChange={(event) =>
                      updateTicketType(
                        ticket.key,
                        'currency',
                        event.target.value,
                      )
                    }
                    className={fieldClass}
                  >
                    <option value="UGX">UGX</option>
                    <option value="KES">KES</option>
                    <option value="RWF">RWF</option>
                    <option value="CDF">CDF</option>
                    <option value="USD">USD</option>
                    <option value="ZMW">ZMW</option>
                    <option value="XAF">XAF</option>
                    <option value="XOF">XOF</option>
                    <option value="SLE">SLE</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => removeTicketType(ticket.key)}
                    disabled={form.ticketTypes.length === 1}
                    className="rounded-xl border border-[#DCE5D8] px-4 py-2 text-sm font-semibold text-[#1A3F22] disabled:opacity-40"
                  >
                    Remove
                  </button>
                </div>
              ))}

              <button
                type="button"
                onClick={addTicketType}
                className="rounded-xl border border-[#58761B] px-4 py-2 text-sm font-semibold text-[#58761B]"
              >
                Add another ticket type
              </button>
            </div>
          )}
        </section>

        <div className="flex items-start gap-3 rounded-xl border border-[#E8E1C7] bg-[#FFFCF1] p-5 text-sm text-[#715B20]">
          <Info size={20} className="mt-0.5 shrink-0" />
          <p>
            Your event will be saved as a draft. Publishing will be
            available when the event publishing workflow is connected.
          </p>
        </div>

        {error && (
          <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex flex-wrap justify-end gap-3">
          <Link
            to="/operations/events"
            className="rounded-xl border border-[#DCE5D8] bg-white px-6 py-3 font-semibold text-[#1A3F22] hover:bg-[#F2F6EF]"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="rounded-xl bg-[#1A3F22] px-6 py-3 font-semibold text-white transition hover:bg-[#31563A] disabled:cursor-wait disabled:opacity-60"
          >
            {saving ? 'Creating event...' : 'Create Event'}
          </button>
        </div>
      </form>
    </div>
  )
}
