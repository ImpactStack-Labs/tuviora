import { useEffect, useMemo, useState } from 'react'
import {
  CalendarDays,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  Clock3,
  Plus,
  RefreshCw,
} from 'lucide-react'

import { getEvents, formatApiError } from '../lib/events'
import {
  createReadinessTask,
  getReadinessTasks,
  updateReadinessTask,
} from '../lib/readiness'

const STATUS_LABELS = {
  pending: 'Pending',
  in_progress: 'In progress',
  completed: 'Completed',
}

const EMPTY_FORM = {
  title: '',
  description: '',
  deadline: '',
}

function formatDateTime(value) {
  if (!value) return 'No deadline'

  return new Intl.DateTimeFormat('en-UG', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function TaskCard({ task, eventId, onUpdated }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function changeStatus(status) {
    if (saving || status === task.status) return

    setSaving(true)
    setError('')

    try {
      const updated = await updateReadinessTask(
        eventId,
        task.id,
        { status },
      )

      onUpdated(updated)
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <article className="rounded-2xl border border-[#E3E9DF] bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 flex-1 gap-3">
          {task.status === 'completed' ? (
            <CheckCircle2
              className="mt-1 shrink-0 text-[#58761B]"
              size={22}
            />
          ) : (
            <Circle
              className="mt-1 shrink-0 text-[#82927D]"
              size={22}
            />
          )}

          <div className="min-w-0">
            <h3 className="font-bold text-[#1A3F22]">
              {task.title}
            </h3>

            {task.description && (
              <p className="mt-1 text-sm text-[#647064]">
                {task.description}
              </p>
            )}

            <p className="mt-3 flex items-center gap-2 text-sm text-[#647064]">
              <CalendarDays size={15} />
              Deadline: {formatDateTime(task.deadline)}
            </p>
          </div>
        </div>

        <span className="rounded-full bg-[#F0F5E9] px-3 py-1 text-xs font-semibold text-[#47651C]">
          {STATUS_LABELS[task.status] || task.status}
        </span>
      </div>

      <div className="mt-5 flex flex-wrap gap-2 border-t border-[#EDF0EA] pt-4">
        {Object.entries(STATUS_LABELS).map(([value, label]) => (
          <button
            key={value}
            type="button"
            disabled={saving || task.status === value}
            onClick={() => changeStatus(value)}
            className={`rounded-lg px-3 py-2 text-sm font-semibold transition disabled:cursor-default ${
              task.status === value
                ? 'bg-[#1A3F22] text-white'
                : 'border border-[#DDE6D6] text-[#1A3F22] hover:bg-[#F0F5E9]'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <p role="alert" className="mt-3 text-sm text-red-700">
          {error}
        </p>
      )}
    </article>
  )
}

export default function EventReadiness() {
  const [events, setEvents] = useState([])
  const [selectedEventId, setSelectedEventId] = useState('')
  const [tasks, setTasks] = useState([])
  const [loadingEvents, setLoadingEvents] = useState(true)
  const [loadingTasks, setLoadingTasks] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [taskError, setTaskError] = useState('')
  const [notice, setNotice] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)

  useEffect(() => {
    let active = true

    getEvents()
      .then((data) => {
        if (!active) return

        const items = Array.isArray(data)
          ? data
          : data.results || []

        setEvents(items)

        if (items.length) {
          setSelectedEventId(String(items[0].id))
        }
      })
      .catch((err) => {
        if (active) setError(formatApiError(err))
      })
      .finally(() => {
        if (active) setLoadingEvents(false)
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!selectedEventId) return

    let active = true

    setLoadingTasks(true)
    setTaskError('')
    setNotice('')
    setTasks([])

    getReadinessTasks(selectedEventId)
      .then((data) => {
        if (!active) return

        setTasks(
          Array.isArray(data) ? data : data.results || [],
        )
      })
      .catch((err) => {
        if (active) setTaskError(formatApiError(err))
      })
      .finally(() => {
        if (active) setLoadingTasks(false)
      })

    return () => {
      active = false
    }
  }, [selectedEventId])

  const selectedEvent = events.find(
    (event) => String(event.id) === selectedEventId,
  )

  const progress = useMemo(() => {
    const completed = tasks.filter(
      (task) => task.status === 'completed',
    ).length

    return {
      completed,
      total: tasks.length,
      percentage: tasks.length
        ? Math.round((completed / tasks.length) * 100)
        : 0,
    }
  }, [tasks])

  async function handleCreate(event) {
    event.preventDefault()

    if (!selectedEventId || saving) return

    setSaving(true)
    setTaskError('')
    setNotice('')

    try {
      const created = await createReadinessTask(
        selectedEventId,
        {
          title: form.title.trim(),
          description: form.description.trim(),
          deadline: new Date(form.deadline).toISOString(),
          status: 'pending',
        },
      )

      setTasks((current) => [...current, created])
      setForm(EMPTY_FORM)
      setShowForm(false)
      setNotice('Readiness task created successfully.')
    } catch (err) {
      setTaskError(formatApiError(err))
    } finally {
      setSaving(false)
    }
  }

  function handleUpdated(updated) {
    setTasks((current) =>
      current.map((task) =>
        task.id === updated.id ? updated : task,
      ),
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-bold uppercase tracking-widest text-[#58761B]">
            Organizer Workspace
          </p>
          <h1 className="text-3xl font-bold text-[#1A3F22]">
            Event Readiness
          </h1>
          <p className="mt-2 text-[#647064]">
            Organize preparation tasks and track event readiness.
          </p>
        </div>

        <button
          type="button"
          disabled={!selectedEventId}
          onClick={() => setShowForm((value) => !value)}
          className="flex items-center gap-2 rounded-xl bg-[#1A3F22] px-5 py-3 font-semibold text-white hover:bg-[#285532] disabled:opacity-50"
        >
          <Plus size={18} />
          Add task
        </button>
      </div>

      {error && (
        <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-700">
          {error}
        </p>
      )}

      {loadingEvents ? (
        <p className="text-[#647064]">Loading your events...</p>
      ) : events.length === 0 ? (
        <div className="rounded-2xl border bg-white p-10 text-center">
          <ClipboardCheck
            className="mx-auto text-[#58761B]"
            size={40}
          />
          <h2 className="mt-4 text-xl font-bold">
            Create an event to get started
          </h2>
          <p className="mt-2 text-[#647064]">
            Readiness tasks are organized under individual events.
          </p>
        </div>
      ) : (
        <>
          <section className="rounded-2xl border border-[#E3E9DF] bg-white p-5">
            <label
              htmlFor="readinessEvent"
              className="mb-2 block font-semibold text-[#1A3F22]"
            >
              Select event
            </label>

            <select
              id="readinessEvent"
              value={selectedEventId}
              onChange={(event) => {
                setSelectedEventId(event.target.value)
                setShowForm(false)
              }}
              className="w-full rounded-xl border border-[#DDE6D6] bg-white px-4 py-3 text-[#1A3F22] outline-none focus:border-[#58761B]"
            >
              {events.map((event) => (
                <option key={event.id} value={event.id}>
                  {event.name} · Event ID: {event.id}
                </option>
              ))}
            </select>

            {selectedEvent && (
              <p className="mt-3 text-sm text-[#647064]">
                {selectedEvent.category} · {selectedEvent.date}
              </p>
            )}
          </section>

          <section className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border bg-white p-5">
              <p className="text-sm text-[#647064]">Total tasks</p>
              <p className="mt-3 text-3xl font-bold text-[#1A3F22]">
                {progress.total}
              </p>
            </div>

            <div className="rounded-2xl border bg-white p-5">
              <p className="text-sm text-[#647064]">
                Completed
              </p>
              <p className="mt-3 text-3xl font-bold text-[#1A3F22]">
                {progress.completed}
              </p>
            </div>

            <div className="rounded-2xl border bg-white p-5">
              <p className="text-sm text-[#647064]">
                Remaining
              </p>
              <p className="mt-3 text-3xl font-bold text-[#1A3F22]">
                {progress.total - progress.completed}
              </p>
            </div>
          </section>

          <section className="rounded-2xl border border-[#E3E9DF] bg-white p-6">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-[#1A3F22]">
                Preparation progress
              </h2>
              <span className="font-bold text-[#58761B]">
                {progress.percentage}%
              </span>
            </div>

            <div className="h-3 overflow-hidden rounded-full bg-[#E9EFE5]">
              <div
                className="h-full rounded-full bg-[#58761B] transition-all"
                style={{ width: `${progress.percentage}%` }}
              />
            </div>

            <p className="mt-3 text-sm text-[#647064]">
              {progress.completed} of {progress.total} tasks completed
            </p>
          </section>

          {showForm && (
            <form
              onSubmit={handleCreate}
              className="space-y-4 rounded-2xl border border-[#DDE6D6] bg-white p-6"
            >
              <h2 className="text-xl font-bold text-[#1A3F22]">
                Add readiness task
              </h2>

              <label className="block">
                <span className="mb-2 block font-semibold">
                  Task title *
                </span>
                <input
                  required
                  maxLength={255}
                  value={form.title}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      title: event.target.value,
                    }))
                  }
                  placeholder="e.g. Confirm venue"
                  className="w-full rounded-xl border border-[#DDE6D6] px-4 py-3"
                />
              </label>

              <label className="block">
                <span className="mb-2 block font-semibold">
                  Description
                </span>
                <textarea
                  rows={3}
                  value={form.description}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      description: event.target.value,
                    }))
                  }
                  className="w-full rounded-xl border border-[#DDE6D6] px-4 py-3"
                />
              </label>

              <label className="block">
                <span className="mb-2 block font-semibold">
                  Deadline *
                </span>
                <input
                  type="datetime-local"
                  required
                  value={form.deadline}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      deadline: event.target.value,
                    }))
                  }
                  className="w-full rounded-xl border border-[#DDE6D6] px-4 py-3"
                />
                <span className="mt-2 block text-xs text-[#647064]">
                  Enter the deadline in your device's local timezone.
                </span>
              </label>

              {taskError && (
                <p role="alert" className="text-sm text-red-700">
                  {taskError}
                </p>
              )}

              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-xl bg-[#1A3F22] px-5 py-3 font-semibold text-white disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Create task'}
                </button>

                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="rounded-xl border px-5 py-3 font-semibold"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}

          {notice && (
            <p
              role="status"
              className="rounded-xl bg-green-50 p-4 text-green-800"
            >
              {notice}
            </p>
          )}

          {taskError && !showForm && (
            <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-700">
              {taskError}
            </p>
          )}

          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-[#1A3F22]">
                Preparation checklist
              </h2>
              <span className="text-sm text-[#647064]">
                {tasks.length} tasks
              </span>
            </div>

            {loadingTasks ? (
              <p className="flex items-center gap-2 text-[#647064]">
                <RefreshCw size={18} className="animate-spin" />
                Loading tasks...
              </p>
            ) : tasks.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[#CCDCC4] bg-white p-10 text-center">
                <Clock3
                  className="mx-auto text-[#58761B]"
                  size={36}
                />
                <h3 className="mt-4 text-lg font-bold text-[#1A3F22]">
                  No preparation tasks yet
                </h3>
                <p className="mt-2 text-[#647064]">
                  Add your first task to start tracking readiness.
                </p>
              </div>
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                {tasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    eventId={selectedEventId}
                    onUpdated={handleUpdated}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
