import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { CheckCircle2, Ticket, RefreshCw } from 'lucide-react'
import { getMyRegistrationTicket } from '../lib/events'

export default function RegistrationTicket({ eventId }) {
  const [ticket, setTicket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadTicket() {
      setLoading(true)
      setError('')

      try {
        const result = await getMyRegistrationTicket(eventId)
        if (active) setTicket(result)
      } catch (err) {
        if (active) {
          setError(
            err.message || 'Unable to load your ticket. Please try again.',
          )
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    loadTicket()

    return () => {
      active = false
    }
  }, [eventId])

  if (loading) {
    return (
      <div role="status" className="mt-5 rounded-2xl border border-border-soft bg-white p-6 text-center">
        <RefreshCw className="mx-auto mb-3 animate-spin" size={24} />
        <p>Preparing your ticket...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div role="alert" className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
        {error}
      </div>
    )
  }

  if (!ticket) return null

  return (
    <section
      aria-label="Your event ticket"
      className="mt-5 overflow-hidden rounded-2xl border border-[#DCE5D8] bg-white shadow-sm"
    >
      <div className="flex items-center gap-3 bg-[#1A3F22] px-5 py-4 text-white">
        <Ticket size={22} aria-hidden="true" />
        <div>
          <h3 className="font-bold">Your event ticket</h3>
          <p className="text-sm text-white/80">
            Present this QR code at the event entrance.
          </p>
        </div>
      </div>

      <div className="flex flex-col items-center gap-5 p-6 text-center">
        {ticket.checked_in ? (
          <div
            role="status"
            className="flex items-center gap-2 rounded-full bg-green-100 px-4 py-2 font-semibold text-green-800"
          >
            <CheckCircle2 size={19} aria-hidden="true" />
            Checked in
          </div>
        ) : (
          <span className="rounded-full bg-[#EDF3E8] px-4 py-2 text-sm font-semibold text-[#1A3F22]">
            Ready for check-in
          </span>
        )}

        <div className="rounded-2xl border border-[#DCE5D8] bg-white p-4">
          <QRCodeSVG
            value={ticket.qr_token}
            size={210}
            level="H"
            marginSize={2}
            title="Event check-in QR code"
          />
        </div>

        <div className="w-full">
          <p className="text-sm text-[#647064]">Ticket reference</p>
          <p className="mt-1 break-all font-mono text-sm font-semibold text-[#1A3F22]">
            {ticket.reference}
          </p>
          <p className="mt-3 text-xs leading-5 text-[#647064]">
            If scanning is unavailable, event staff can enter this reference
            manually. Keep your ticket private.
          </p>
        </div>
      </div>
    </section>
  )
}
