import { useEffect } from 'react'
import {
  MapContainer,
  Marker,
  TileLayer,
  useMap,
  useMapEvents,
} from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const DEFAULT_CENTER = [0.3476, 32.5825] // Kampala

const venueIcon = L.divIcon({
  className: '',
  html: `
    <div style="
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      border-radius: 50% 50% 50% 0;
      background: #1A3F22;
      border: 3px solid white;
      box-shadow: 0 3px 12px rgba(0,0,0,.25);
      transform: rotate(-45deg);
    ">
      <span style="
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: white;
      "></span>
    </div>
  `,
  iconSize: [34, 34],
  iconAnchor: [17, 34],
})

function LocationPicker({ onChange }) {
  useMapEvents({
    click(event) {
      onChange({
        latitude: Number(event.latlng.lat.toFixed(6)),
        longitude: Number(event.latlng.lng.toFixed(6)),
      })
    },
  })

  return null
}

function RecenterMap({ position }) {
  const map = useMap()

  useEffect(() => {
    if (position) {
      map.flyTo(position, Math.max(map.getZoom(), 13))
    }
  }, [map, position?.[0], position?.[1]])

  return null
}

export default function VenueMap({
  latitude,
  longitude,
  onLocationChange,
}) {
  const hasLocation =
    Number.isFinite(latitude) &&
    Number.isFinite(longitude)

  const position = hasLocation
    ? [latitude, longitude]
    : null

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200">
      <MapContainer
        center={position || DEFAULT_CENTER}
        zoom={12}
        scrollWheelZoom={false}
        className="h-80 w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <LocationPicker onChange={onLocationChange} />

        {position && (
          <>
            <Marker position={position} icon={venueIcon} />
            <RecenterMap position={position} />
          </>
        )}
      </MapContainer>

      <div className="bg-white px-4 py-3 text-sm text-gray-600">
        {position
          ? `Selected location: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}`
          : 'Click anywhere on the map to select your event venue.'}
      </div>
    </div>
  )
}
