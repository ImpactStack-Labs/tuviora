import { Link, NavLink } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { navigation } from './navigation'

export default function Sidebar({ closeMenu }) {
  return (
    <div className="flex h-full flex-col bg-[#1A3F22] text-white">
      <Link to="/" className="px-6 py-8 text-3xl font-bold">
        tuviora<span className="text-[#D99201]">.</span>
      </Link>

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
