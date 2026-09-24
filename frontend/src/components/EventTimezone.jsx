import { useMemo } from 'react'

export const EVENT_TIMEZONES = [
  { value: 'Africa/Kampala', label: 'East Africa Time · Kampala (UTC+3)' },
  { value: 'Africa/Nairobi', label: 'East Africa Time · Nairobi (UTC+3)' },
  { value: 'Africa/Kigali', label: 'Central Africa Time · Kigali (UTC+2)' },
  { value: 'Africa/Johannesburg', label: 'South Africa Time · Johannesburg (UTC+2)' },
  { value: 'Africa/Lagos', label: 'West Africa Time · Lagos (UTC+1)' },
  { value: 'Africa/Accra', label: 'Greenwich Mean Time · Accra (UTC+0)' },
  { value: 'Europe/London', label: 'London · UK time' },
  { value: 'Europe/Paris', label: 'Paris · Central European time' },
  { value: 'America/New_York', label: 'New York · Eastern time' },
  { value: 'America/Los_Angeles', label: 'Los Angeles · Pacific time' },
  { value: 'Asia/Dubai', label: 'Dubai · Gulf Standard Time (UTC+4)' },
  { value: 'Asia/Kolkata', label: 'India Standard Time (UTC+5:30)' },
]

export function formatEventTimezone(timezone, date) {
  const zone = timezone || 'Africa/Kampala'

  try {
    const dateTime = new Date(`${date || '2026-01-15'}T12:00:00Z`)

    const name = new Intl.DateTimeFormat('en-GB', {
      timeZone: zone,
      timeZoneName: 'long',
    })
      .formatToParts(dateTime)
      .find((part) => part.type === 'timeZoneName')?.value

    const offset = new Intl.DateTimeFormat('en-GB', {
      timeZone: zone,
      timeZoneName: 'shortOffset',
    })
      .formatToParts(dateTime)
      .find((part) => part.type === 'timeZoneName')?.value

    const normalizedOffset = offset
      ? offset.replace('GMT', 'UTC')
      : ''

    return `${name || zone}${normalizedOffset ? ` (${normalizedOffset})` : ''}`
  } catch {
    return zone
  }
}

export default function EventTimezone({
  value = 'Africa/Kampala',
  onChange,
  date,
}) {
  const selectedLabel = useMemo(
    () => formatEventTimezone(value, date),
    [value, date],
  )

  return (
    <div className="space-y-2">
      <label
        htmlFor="eventTimezone"
        className="block font-semibold"
      >
        Event timezone
        <span className="ml-1 text-red-600">*</span>
      </label>

      <select
        id="eventTimezone"
        name="timezone"
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-gray-900 outline-none transition focus:border-[#58761B] focus:ring-2 focus:ring-[#58761B]/20"
      >
        {EVENT_TIMEZONES.map((zone) => (
          <option key={zone.value} value={zone.value}>
            {zone.label}
          </option>
        ))}
      </select>

      <p className="text-sm text-gray-600">
        Event times will use {selectedLabel}.
        Choose the timezone where the event takes place.
      </p>
    </div>
  )
}
