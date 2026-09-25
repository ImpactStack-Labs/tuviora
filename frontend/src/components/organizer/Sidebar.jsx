import TuvioraLogo from '../TuvioraLogo'
import { Link, NavLink } from 'react-router-dom'
import { ArrowLeft, LogOut, UserRound } from 'lucide-react'
import { navigation } from './navigation'

export default function Sidebar({
  closeMenu,
  user,
  onLogout,
  signingOut = false,
}) {
  return (
    <div className="flex h-full flex-col bg-[#1A3F22] text-white">
      <div className="px-6 py-7">
        <TuvioraLogo dark imageClassName="h-10 w-auto max-w-[160px]" />
      </div>

      <p className="px-6 pb-4 text-xs font-semibold uppercase tracking-widest text-[#B8CBB8]">
        Organizer Workspace
      </p>

      <nav className="flex-1 space-y-1 px-3">
        {navigation.map(({ name, path, icon: Icon }) => (
          <NavLink
            key={name}
            to={path ? `/operations/${path}` : '/operations'}
            end={!path}
            onClick={closeMenu}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-4 py-3 text-sm transition-colors ${
                isActive
                  ? 'bg-[#365B40] font-semibold text-white'
                  : 'text-[#DCE9DC] hover:bg-[#2D5136]'
              }`
            }
          >
            <Icon size={19} />
            {name}
          </NavLink>
        ))}
      </nav>

      <div className="mx-4 border-t border-white/20 px-3 pt-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#365B40]">
            <UserRound size={20} />
          </div>

          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">
              {user?.username || 'Account'}
            </p>
            <p className="text-xs text-[#B8CBB8]">
              {user?.is_organizer ? 'Organizer' : 'Event team'}
            </p>
          </div>
        </div>

        <button
          type="button"
          disabled={signingOut}
          onClick={onLogout}
          className="mt-4 flex w-full items-center gap-2 rounded-lg border border-white/20 px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#365B40] disabled:opacity-50"
        >
          <LogOut size={18} />
          {signingOut ? 'Signing out...' : 'Sign out'}
        </button>
      </div>

      <Link
        to="/"
        className="m-4 flex items-center gap-2 border-t border-white/20 px-3 pt-5 text-sm text-[#DCE9DC]"
      >
        <ArrowLeft size={18} />
        Back to website
      </Link>
    </div>
  )
}
