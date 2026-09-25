import { useState } from 'react'
import { logoutOrganizer } from '../lib/auth'
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
import EventAttendance from '../pages/EventAttendance'
import LiveOperations from '../pages/LiveOperations'
import IncidentManagement from '../pages/IncidentManagement'
import Communications from '../pages/Communications'
import FeedbackPage from '../pages/FeedbackPage'

// Sidebar paths that have a real page; the rest render the placeholder.
const builtPaths = new Set([
  'events', 'readiness', 'team', 'registration', 'attendance',
  'live', 'incidents', 'communications', 'feedback',
])

export default function OrganizerLayout({ user, onLogout }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)
  const [logoutError, setLogoutError] = useState('')

  async function handleLogout() {
    if (signingOut) return

    setSigningOut(true)
    setLogoutError('')

    try {
      await logoutOrganizer()
      onLogout()
    } catch (err) {
      setLogoutError(
        err.message || 'Unable to sign out. Please try again.',
      )
    } finally {
      setSigningOut(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F7F9F5] text-[#1A3F22]">
      <aside className="fixed inset-y-0 left-0 hidden w-64 overflow-y-auto lg:block">
        <Sidebar
          user={user}
          onLogout={handleLogout}
          signingOut={signingOut}
        />
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
            <Sidebar
              closeMenu={() => setMenuOpen(false)}
              user={user}
              onLogout={handleLogout}
              signingOut={signingOut}
            />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="flex min-h-20 flex-wrap items-center justify-between gap-3 border-b border-border-soft bg-white px-5 py-3 sm:px-8">
          <div className="flex items-center gap-4">
            <button
              type="button"
              aria-label="Open navigation"
              onClick={() => setMenuOpen(true)}
              className="lg:hidden"
            >
              <Menu size={25} />
            </button>
            <p className="font-bold">Organizer Workspace</p>
          </div>

          <div className="flex items-center gap-2">
            <ApiStatus />
            <span className="hidden rounded-full bg-[#EDF3E8] px-4 py-2 text-xs font-semibold text-[#58761B] sm:inline-flex">
              Organizer workspace
            </span>
          </div>
        </header>

        {logoutError && (
          <div
            role="alert"
            className="mx-auto mt-5 max-w-[1500px] rounded-lg bg-red-50 px-5 py-3 text-sm text-red-700"
          >
            {logoutError}
          </div>
        )}

        <main className="mx-auto max-w-[1500px] px-5 py-8 sm:px-8">
          <Routes>
            <Route index element={<OrganizerOverview />} />
            <Route path="events" element={<MyEvents />} />
            <Route path="events/new" element={<CreateEvent />} />
            <Route path="readiness" element={<EventReadiness />} />
            <Route path="team" element={<EventTeam />} />
            <Route path="registration" element={<EventRegistrations />} />
            <Route path="attendance" element={<EventAttendance />} />
            <Route path="live" element={<LiveOperations />} />
            <Route path="incidents" element={<IncidentManagement />} />
            <Route path="communications" element={<Communications />} />
            <Route path="feedback" element={<FeedbackPage />} />
            {navigation.slice(1).filter(({ path }) => !builtPaths.has(path)).map(({ name, path }) => (
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
