import { RefreshCw } from 'lucide-react'

export default function LoadingRow({ label = 'Loading...', className = '' }) {
  return (
    <p
      role="status"
      className={`inline-flex items-center gap-2 text-text-muted ${className}`}
    >
      <RefreshCw size={18} className="animate-spin" />
      {label}
    </p>
  )
}
