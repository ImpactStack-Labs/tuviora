import { ClipboardCheck } from 'lucide-react'
import EmptyState from '../components/EmptyState'

export default function OrganizerModule({ title }) {
  return (
    <div>
      <p className="mb-2 font-semibold uppercase tracking-widest text-[#58761B]">
        Organizer workspace
      </p>
      <h1 className="text-3xl font-bold">{title}</h1>
      <div className="mt-8">
        <EmptyState
          as="h2"
          size="lg"
          icon={ClipboardCheck}
          title={`${title} is being developed`}
          description="This module is ready for its upcoming backend integration."
        />
      </div>
    </div>
  )
}
