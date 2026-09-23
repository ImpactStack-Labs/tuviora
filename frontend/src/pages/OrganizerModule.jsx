import { ClipboardCheck } from 'lucide-react'

export default function OrganizerModule({ title }) {
  return (
    <div>
      <p className="mb-2 font-semibold text-[#58761B]">
        Organizer Workspace
      </p>
      <h1 className="text-3xl font-bold">{title}</h1>
      <div className="mt-8 rounded-2xl border border-[#E3E9DF] bg-white p-12 text-center">
        <ClipboardCheck
          size={36}
          className="mx-auto text-[#58761B]"
        />
        <h2 className="mt-5 text-xl font-bold">
          {title} is being developed
        </h2>
        <p className="mt-3 text-[#647064]">
          This module is ready for its upcoming backend integration.
        </p>
      </div>
    </div>
  )
}
