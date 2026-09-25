import { useEffect, useRef, useState } from 'react'
import { Camera, CameraOff } from 'lucide-react'

export default function TicketQrScanner({ onScan, disabled = false }) {
  const scannerRef = useRef(null)
  const onScanRef = useRef(onScan)
  const startingRef = useRef(false)
  const [active, setActive] = useState(false)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    onScanRef.current = onScan
  }, [onScan])

  useEffect(() => {
    return () => {
      const scanner = scannerRef.current
      scannerRef.current = null

      if (scanner) {
        scanner.stop()
          .catch(() => {})
          .finally(() => scanner.clear().catch(() => {}))
      }
    }
  }, [])

  async function stopCamera() {
    startingRef.current = false
    const scanner = scannerRef.current
    scannerRef.current = null
    setActive(false)
    setStarting(false)

    if (!scanner) return

    try {
      await scanner.stop()
    } catch {
      // The camera may already have stopped.
    }

    try {
      await scanner.clear()
    } catch {
      // The scanner element may already be unmounted.
    }
  }

  async function startCamera() {
    if (disabled || startingRef.current || scannerRef.current) return

    startingRef.current = true
    setStarting(true)
    setError('')

    try {
      const { Html5Qrcode } = await import('html5-qrcode')

      if (!startingRef.current) return

      const scanner = new Html5Qrcode('tuviora-ticket-scanner')
      scannerRef.current = scanner

      await scanner.start(
        { facingMode: 'environment' },
        {
          fps: 10,
          qrbox: { width: 220, height: 220 },
        },
        (decodedText) => {
          if (!startingRef.current) return

          startingRef.current = false
          onScanRef.current(decodedText.trim())
          void stopCamera()
        },
        () => {
          // Ignore individual frames without a QR code.
        },
      )

      if (scannerRef.current === scanner) {
        startingRef.current = true
        setActive(true)
      } else {
        await scanner.stop().catch(() => {})
        await scanner.clear().catch(() => {})
      }
    } catch {
      setError(
        'Camera unavailable. Check browser permissions or enter the ticket reference manually.',
      )
      await stopCamera()
    } finally {
      setStarting(false)
    }
  }

  return (
    <section className="rounded-2xl border border-border-soft bg-white p-6">
      <div className="mb-4 flex items-center gap-3">
        <Camera size={24} className="text-[#58761B]" />
        <div>
          <h2 className="text-xl font-bold text-[#1A3F22]">
            Scan a QR ticket
          </h2>
          <p className="text-sm text-[#718072]">
            Use your camera to read an attendee's ticket.
          </p>
        </div>
      </div>

      <div
        id="tuviora-ticket-scanner"
        className={active || starting ? 'mb-4 overflow-hidden rounded-xl' : 'hidden'}
      />

      {error && (
        <p role="alert" className="mb-4 text-sm text-red-700">
          {error}
        </p>
      )}

      {active || starting ? (
        <button
          type="button"
          onClick={stopCamera}
          className="inline-flex items-center gap-2 rounded-xl border border-red-300 px-4 py-3 font-semibold text-red-700"
        >
          <CameraOff size={18} />
          {starting ? 'Starting camera...' : 'Stop camera'}
        </button>
      ) : (
        <button
          type="button"
          onClick={startCamera}
          disabled={disabled}
          className="inline-flex items-center gap-2 rounded-xl bg-[#1A3F22] px-4 py-3 font-semibold text-white disabled:opacity-50"
        >
          <Camera size={18} />
          Start camera
        </button>
      )}
    </section>
  )
}
