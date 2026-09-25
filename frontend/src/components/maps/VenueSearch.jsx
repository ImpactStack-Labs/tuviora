import { useEffect, useRef, useState } from 'react'
import { MapPin, Search } from 'lucide-react'

const SEARCH_ENDPOINT =
  'https://nominatim.openstreetmap.org/search'

export default function VenueSearch({
  venue,
  landmark,
  onLocationSelect,
}) {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const controllerRef = useRef(null)

  useEffect(() => {
    return () => controllerRef.current?.abort()
  }, [])

  async function findVenue() {
    if (!venue.trim()) {
      setError('Enter a venue name before searching.')
      return
    }

    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setLoading(true)
    setError('')
    setResults([])

    const query = [venue, landmark, 'Uganda']
      .filter(Boolean)
      .join(', ')

    const params = new URLSearchParams({
      q: query,
      format: 'jsonv2',
      limit: '5',
      addressdetails: '1',
      countrycodes: 'ug',
    })

    try {
      const response = await fetch(
        `${SEARCH_ENDPOINT}?${params}`,
        { signal: controller.signal },
      )

      if (!response.ok) {
        throw new Error('Venue search is temporarily unavailable.')
      }

      const data = await response.json()

      if (!Array.isArray(data) || data.length === 0) {
        setError(
          'No matching venue found. Try a shorter name or select it manually on the map.',
        )
        return
      }

      setResults(data)
    } catch (searchError) {
      if (searchError.name !== 'AbortError') {
        setError(
          searchError.message ||
            'Unable to search for this venue.',
        )
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false)
      }
    }
  }

  function selectVenue(result) {
    const latitude = Number(result.lat)
    const longitude = Number(result.lon)

    if (
      !Number.isFinite(latitude) ||
      !Number.isFinite(longitude)
    ) {
      setError('This location has invalid coordinates.')
      return
    }

    onLocationSelect({
      latitude,
      longitude,
    })

    setResults([])
    setError('')
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={findVenue}
        disabled={loading || !venue.trim()}
        className="inline-flex items-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#315C38] disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Search size={17} />
        {loading ? 'Finding venue...' : 'Find venue on map'}
      </button>

      {error && (
        <p role="alert" className="text-sm text-[#A34327]">
          {error}
        </p>
      )}

      {results.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border-soft bg-white">
          <p className="border-b border-border-soft px-4 py-3 text-sm font-semibold text-[#1A3F22]">
            Select the correct location
          </p>

          <div className="divide-y divide-[#E3E9DF]">
            {results.map((result) => (
              <button
                key={result.place_id}
                type="button"
                onClick={() => selectVenue(result)}
                className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-[#F2F6EF]"
              >
                <MapPin
                  size={19}
                  className="mt-0.5 shrink-0 text-[#58761B]"
                />
                <span className="text-sm text-[#1A3F22]">
                  {result.display_name}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-[#647064]">
        Search results from OpenStreetMap contributors.
        If your venue isn't listed, select its location
        manually on the map.
      </p>
    </div>
  )
}
