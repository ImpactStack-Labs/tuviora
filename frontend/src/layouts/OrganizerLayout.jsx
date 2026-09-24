import { useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import ApiStatus from '../components/ApiStatus'
import Sidebar from '../components/organizer/Sidebar'
import { navigation } from '../components/organizer/navigation'
import OrganizerOverview from '../pages/OrganizerOverview'
import OrganizerModule from '../pages/OrganizerModule'
import MyEvents from '../pages/MyEvents'
import CreateEvent from '../pages/CreateEvent'
import EventReadiness from '../pages/EventReadiness'
import EventTeam from '../pages/EventTeam'
import EventRegistrations from '../pages/EventRegistrations'

export default function OrganizerLayout() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[#F7F9F5] text-[#1A3F22]">
      <aside className="fixed inset-y-0 left-0 hidden w-64 overflow-y-auto lg:block">
        <Sidebar />
      </aside>

      {menuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setMenuOpen(false)}
            className="absolute inset-0 bg-black/50"
          />
          <aside className="relative h-full w-72 max-w-[85vw] overflow-y-auto">
            <button
              type="button"
              aria-label="Close menu"
              onClick={() => setMenuOpen(false)}
              className="absolute right-4 top-6 z-10 text-white"
            >
              <X size={24} />
            </button>
            <Sidebar closeMenu={() => setMenuOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="flex h-20 items-center justify-between border-b border-[#E3E9DF] bg-white px-5 sm:px-8">
          <div className="flex items-center gap-4">
            <button
              type="button"
              aria-label="Open navigation"
              onClick={() => setMenuOpen(true)}
              className="lg:hidden"
            >
              <Menu size={25} />
            </button>
            <div>
              <p className="text-xs text-[#718072]">ImpactStack Labs</p>
              <p className="font-bold">Organizer Workspace</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <ApiStatus />
            <span className="rounded-full bg-[#EDF3E8] px-4 py-2 text-xs font-semibold text-[#58761B]">
            Foundation Preview
          </span>
          </div>
        </header>

        <main className="mx-auto max-w-[1500px] px-5 py-8 sm:px-8">
          <Routes>
            <Route index element={<OrganizerOverview />} />
            <Route path="events" element={<MyEvents />} />
            <Route path="events/new" element={<CreateEvent />} />
            <Route path="readiness" element={<EventReadiness />} />
            <Route path="team" element={<EventTeam />} />
            <Route path="registration" element={<EventRegistrations />} />
            {navigation.slice(1).filter(({ path }) => path !== 'events' && path !== 'readiness' && path !== 'team' && path !== 'registration').map(({ name, path }) => (
              <Route
                key={path}
                path={path}
                element={<OrganizerModule title={name} />}
              />
            ))}
          </Routes>
        </main>
      </div>
    </div>
  )
}
