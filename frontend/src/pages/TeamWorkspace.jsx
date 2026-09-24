import { useEffect, useMemo, useState } from 'react'
import {
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  LogOut,
  RefreshCw,
  Users,
} from 'lucide-react'
import { apiRequest, logoutOrganizer } from '../lib/auth'

const STATUS_LABELS = {
  pending: 'Pending',
  in_progress: 'In progress',
  completed: 'Completed',
}

function formatDeadline(value) {
  if (!value) return 'No deadline'

  return new Intl.DateTimeFormat('en-UG', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export default function TeamWorkspace({ user, onLogout }) {
  const memberships = user.team_memberships || []
  const [selectedEventId, setSelectedEventId] = useState(
    memberships[0]?.event_id || '',
  )
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [savingTaskId, setSavingTaskId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const selectedMembership = memberships.find(
    (membership) =>
      String(membership.event_id) === String(selectedEventId),
  )

  useEffect(() => {
    if (!selectedEventId) return

    let active = true

    setLoading(true)
    setError('')
    setTasks([])

    apiRequest(`/api/events/${selectedEventId}/tasks/`)
      .then((data) => {
        if (!active) return
        setTasks(Array.isArray(data) ? data : data.results || [])
      })
      .catch((err) => {
        if (active) setError(err.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [selectedEventId])

  const completed = useMemo(
    () => tasks.filter((task) => task.status === 'completed').length,
    [tasks],
  )

  async function updateStatus(task, status) {
    if (savingTaskId !== null || task.status === status) return

    setSavingTaskId(task.id)
    setError('')
    setNotice('')

    try {
      const updated = await apiRequest(
        `/api/events/${selectedEventId}/tasks/${task.id}/`,
        {
          method: 'PATCH',
          body: JSON.stringify({ status }),
        },
      )

      setTasks((current) =>
        current.map((item) =>
          item.id === updated.id ? updated : item,
        ),
      )

      setNotice('Task progress updated.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingTaskId(null)
    }
  }

  async function handleLogout() {
    try {
      await logoutOrganizer()
      onLogout()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="min-h-screen bg-[#F7F9F5] text-[#1A3F22]">
      <header className="border-b border-[#E3E9DF] bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-[#58761B]">
              Tuviora
            </p>
            <h1 className="mt-1 text-2xl font-bold">
              Team Workspace
            </h1>
            <p className="mt-1 text-sm text-[#647064]">
              Welcome, {user.username}
            </p>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="inline-flex items-center gap-2 rounded-xl border border-[#DDE6D6] px-4 py-2 text-sm font-semibold hover:bg-[#F0F5E9]"
          >
            <LogOut size={17} />
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold">
            Your events and tasks
          </h2>
          <p className="mt-2 text-[#647064]">
            View your responsibilities and keep your event
            organizer informed of your progress.
          </p>
        </div>

        {memberships.length > 0 && (
          <section className="mb-7 rounded-2xl border border-[#E3E9DF] bg-white p-5">
            <label
              htmlFor="team-event"
              className="mb-2 block text-sm font-semibold"
            >
              My event
            </label>

            <select
              id="team-event"
              value={selectedEventId}
              onChange={(event) =>
                setSelectedEventId(event.target.value)
              }
              className="w-full rounded-xl border border-[#DDE6D6] bg-white px-4 py-3 sm:max-w-md"
            >
              {memberships.map((membership) => (
                <option
                  key={membership.event_id}
                  value={membership.event_id}
                >
                  {membership.event_name}
                </option>
              ))}
            </select>

            {selectedMembership && (
              <p className="mt-3 text-sm text-[#647064]">
                Your role:{' '}
                <span className="font-semibold text-[#1A3F22]">
                  {selectedMembership.role === 'manager'
                    ? 'Event Manager'
                    : 'Team Member'}
                </span>
              </p>
            )}
          </section>
        )}

        <div className="mb-8 grid gap-4 sm:grid-cols-3">
          {[
            {
              label: 'My events',
              value: memberships.length,
              Icon: Users,
            },
            {
              label: 'Visible tasks',
              value: tasks.length,
              Icon: ClipboardCheck,
            },
            {
              label: 'Completed',
              value: tasks.length
                ? `${Math.round((completed / tasks.length) * 100)}%`
                : '0%',
              Icon: CheckCircle2,
            },
          ].map(({ label, value, Icon }) => (
            <div
              key={label}
              className="rounded-2xl border border-[#E3E9DF] bg-white p-5"
            >
              <Icon size={23} className="text-[#58761B]" />
              <p className="mt-4 text-3xl font-bold">{value}</p>
              <p className="mt-1 text-sm text-[#647064]">
                {label}
              </p>
            </div>
          ))}
        </div>

        {error && (
          <p role="alert" className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">
            {error}
          </p>
        )}

        {notice && (
          <p role="status" className="mb-5 rounded-xl bg-green-50 p-4 text-sm text-green-800">
            {notice}
          </p>
        )}

        <section>
          <h2 className="mb-5 text-xl font-bold">
            {selectedMembership?.role === 'manager'
              ? 'Event readiness tasks'
              : 'My assigned tasks'}
          </h2>

          {loading ? (
            <p className="flex items-center gap-2 text-[#647064]">
              <RefreshCw size={18} className="animate-spin" />
              Loading tasks...
            </p>
          ) : tasks.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[#CCD8C4] bg-white p-10 text-center">
              <ClipboardCheck
                size={36}
                className="mx-auto text-[#58761B]"
              />
              <h3 className="mt-4 font-bold">
                No tasks to display yet
              </h3>
              <p className="mt-2 text-sm text-[#647064]">
                Tasks will appear here when your organizer
                assigns them to you.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {tasks.map((task) => (
                <article
                  key={task.id}
                  className="rounded-2xl border border-[#E3E9DF] bg-white p-5 shadow-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <h3 className="font-bold">{task.title}</h3>
                    <span className="rounded-full bg-[#F0F5E9] px-3 py-1 text-xs font-semibold text-[#47651C]">
                      {STATUS_LABELS[task.status] || task.status}
                    </span>
                  </div>

                  {task.description && (
                    <p className="mt-3 text-sm text-[#647064]">
                      {task.description}
                    </p>
                  )}

                  <p className="mt-4 flex items-center gap-2 text-sm text-[#647064]">
                    <CalendarDays size={16} />
                    {formatDeadline(task.deadline)}
                  </p>

                  <div className="mt-5 flex flex-wrap gap-2 border-t border-[#EDF0EA] pt-4">
                    {Object.entries(STATUS_LABELS).map(
                      ([value, label]) => (
                        <button
                          key={value}
                          type="button"
                          disabled={
                            savingTaskId !== null ||
                            task.status === value
                          }
                          onClick={() =>
                            updateStatus(task, value)
                          }
                          className={`rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-60 ${
                            task.status === value
                              ? 'bg-[#1A3F22] text-white'
                              : 'border border-[#DDE6D6] hover:bg-[#F0F5E9]'
                          }`}
                        >
                          {label}
                        </button>
                      ),
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
