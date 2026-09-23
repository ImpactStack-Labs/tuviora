import { useEffect, useState } from 'react'
import { getApiHealth } from '../lib/api'

export default function ApiStatus() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    const controller = new AbortController()

    getApiHealth(controller.signal)
      .then(() => setStatus('connected'))
      .catch((error) => {
        if (error.name !== 'AbortError') {
          setStatus('offline')
        }
      })

    return () => controller.abort()
  }, [])

  const states = {
    checking: {
      label: 'Checking API',
      dot: 'bg-amber-500',
      style: 'bg-amber-50 text-amber-800',
    },
    connected: {
      label: 'API Connected',
      dot: 'bg-green-600',
      style: 'bg-green-50 text-green-800',
    },
    offline: {
      label: 'API Offline',
      dot: 'bg-red-500',
      style: 'bg-red-50 text-red-800',
    },
  }

  const current = states[status]

  return (
    <span
      role="status"
      className={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold ${current.style}`}
    >
      <span
        className={`h-2 w-2 rounded-full ${current.dot}`}
        aria-hidden="true"
      />
      {current.label}
    </span>
  )
}
