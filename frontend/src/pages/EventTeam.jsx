import { useEffect, useState } from 'react'
import {
  Check,
  ClipboardCopy,
  MailPlus,
  RefreshCw,
  ShieldCheck,
  UserRound,
  Users,
  XCircle,
} from 'lucide-react'
import { getEvents, formatApiError } from '../lib/events'
import { formatDateTime } from '../lib/format'
import StatCard from '../components/StatCard'
import {
  createEventInvitation,
  getEventInvitations,
  getEventTeam,
  revokeEventInvitation,
} from '../lib/team'

const ROLE_LABELS = {
  organizer: 'Organizer',
  manager: 'Event Manager',
  member: 'Team Member',
}

function invitationStatus(invitation) {
  if (invitation.accepted_at) return 'Accepted'
  if (invitation.revoked_at) return 'Revoked'
  if (new Date(invitation.expires_at).getTime() <= Date.now()) {
    return 'Expired'
  }
  return 'Pending'
}

export default function EventTeam() {
  const [events, setEvents] = useState([])
  const [selectedEventId, setSelectedEventId] = useState('')
  const [members, setMembers] = useState([])
  const [invitations, setInvitations] = useState([])
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('member')
  const [loadingEvents, setLoadingEvents] = useState(true)
  const [loadingTeam, setLoadingTeam] = useState(false)
  const [saving, setSaving] = useState(false)
  const [revokingId, setRevokingId] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [inviteLink, setInviteLink] = useState('')
  const [copied, setCopied] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let active = true

    getEvents()
      .then((data) => {
        if (!active) return
        const list = Array.isArray(data) ? data : data.results || []
        setEvents(list)
        if (list.length) setSelectedEventId(String(list[0].id))
      })
      .catch((err) => {
        if (active) setError(formatApiError(err))
      })
      .finally(() => {
        if (active) setLoadingEvents(false)
      })

    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!selectedEventId) return

    let active = true

    Promise.all([
      getEventTeam(selectedEventId),
      getEventInvitations(selectedEventId),
    ])
      .then(([team, invites]) => {
        if (!active) return
        setMembers(team)
        setInvitations(invites)
      })
      .catch((err) => {
        if (active) setError(formatApiError(err))
      })
      .finally(() => {
        if (active) setLoadingTeam(false)
      })

    return () => { active = false }
  }, [selectedEventId, refreshKey])

  const selectedEvent = events.find(
    (event) => String(event.id) === selectedEventId,
  )

  const pendingCount = invitations.filter(
    (item) => invitationStatus(item) === 'Pending',
  ).length

  async function handleInvite(event) {
    event.preventDefault()
    if (!selectedEventId || saving) return

    setSaving(true)
    setError('')
    setNotice('')
    setInviteLink('')
    setCopied(false)

    try {
      const result = await createEventInvitation(selectedEventId, {
        email: email.trim(),
        role,
      })

      const link = new URL(
        `/invite#token=${encodeURIComponent(result.invitation_token)}`,
        window.location.origin,
      ).toString()

      setInviteLink(link)
      setEmail('')
      setNotice('Invitation created. Copy and share the private link.')
      setRefreshKey((value) => value + 1)
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(inviteLink)
      setCopied(true)
    } catch {
      setError('Could not copy automatically. Select and copy the link below.')
    }
  }

  async function handleRevoke(invitationId) {
    if (!window.confirm('Revoke this invitation?')) return

    setRevokingId(invitationId)
    setError('')
    setNotice('')

    try {
      await revokeEventInvitation(selectedEventId, invitationId)
      setNotice('Invitation revoked.')
      setRefreshKey((value) => value + 1)
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setRevokingId(null)
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
            People and responsibilities
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
            Event Team
          </h1>
          <p className="mt-3 max-w-2xl text-text-muted">
            Bring your event team together, manage invitations and prepare
            to assign responsibilities.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setLoadingTeam(true)
            setError('')
            setRefreshKey((value) => value + 1)
          }}
          disabled={!selectedEventId || loadingTeam}
          className="inline-flex items-center gap-2 rounded-xl border border-border-soft bg-white px-4 py-3 text-sm font-semibold disabled:opacity-50"
        >
          <RefreshCw size={17} /> Refresh
        </button>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}
      {notice && (
        <div role="status" className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          {notice}
        </div>
      )}

      <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
        <label htmlFor="team-event" className="mb-2 block text-sm font-semibold">
          Select an event
        </label>
        <select
          id="team-event"
          value={selectedEventId}
          onChange={(event) => {
            setLoadingTeam(true)
            setError('')
            setMembers([])
            setInvitations([])
            setSelectedEventId(event.target.value)
            setInviteLink('')
            setNotice('')
          }}
          disabled={loadingEvents || !events.length}
          className="w-full rounded-xl border border-border-soft bg-white px-4 py-3 outline-none focus:border-[#58761B] sm:max-w-xl"
        >
          {!events.length && <option value="">No events available</option>}
          {events.map((event) => (
            <option key={event.id} value={String(event.id)}>
              {event.name}
            </option>
          ))}
        </select>
        {selectedEvent && (
          <p className="mt-3 text-sm text-text-muted">
            {selectedEvent.category} · {selectedEvent.date}
          </p>
        )}
      </section>

      {selectedEventId && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              { label: 'Team members', value: members.length, icon: Users },
              { label: 'Pending invitations', value: pendingCount, icon: MailPlus },
              { label: 'Event managers', value: members.filter((member) => member.role === 'manager').length, icon: ShieldCheck },
            ].map(({ label, value, icon: Icon }) => (
              <StatCard
                key={label}
                label={label}
                value={loadingTeam ? '…' : value}
                icon={Icon}
              />
            ))}
          </div>

          <div className="grid items-start gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
              <h2 className="text-xl font-bold">Team members</h2>
              <p className="mt-1 text-sm text-text-muted">
                Everyone who has joined this event.
              </p>

              <div className="mt-6 divide-y divide-[#EDF1EA]">
                {!loadingTeam && !members.length && (
                  <p className="py-6 text-sm text-text-muted">
                    No team members found.
                  </p>
                )}
                {members.map((member) => (
                  <div key={member.user_id} className="flex items-center gap-4 py-4">
                    <div className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-[#EDF3E8] text-[#58761B]">
                      <UserRound size={21} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{member.username}</p>
                      <p className="truncate text-sm text-text-muted">
                        {member.email || 'No email provided'}
                      </p>
                    </div>
                    <span className="rounded-full bg-[#EDF3E8] px-3 py-1.5 text-xs font-semibold text-[#58761B]">
                      {ROLE_LABELS[member.role] || member.role}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
              <div className="mb-6 flex items-center gap-3">
                <div className="rounded-xl bg-[#EDF3E8] p-3 text-[#58761B]">
                  <MailPlus size={22} />
                </div>
                <div>
                  <h2 className="text-xl font-bold">Invite a teammate</h2>
                  <p className="text-sm text-text-muted">
                    Generate a private invitation link.
                  </p>
                </div>
              </div>

              <form onSubmit={handleInvite} className="space-y-5">
                <div>
                  <label htmlFor="invite-email" className="mb-2 block text-sm font-semibold">
                    Email address
                  </label>
                  <input
                    id="invite-email"
                    type="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="teammate@example.com"
                    className="w-full rounded-xl border border-border-soft px-4 py-3 outline-none focus:border-[#58761B]"
                  />
                </div>
                <div>
                  <label htmlFor="invite-role" className="mb-2 block text-sm font-semibold">
                    Event role
                  </label>
                  <select
                    id="invite-role"
                    value={role}
                    onChange={(event) => setRole(event.target.value)}
                    className="w-full rounded-xl border border-border-soft bg-white px-4 py-3 outline-none focus:border-[#58761B]"
                  >
                    <option value="member">Team Member</option>
                    <option value="manager">Event Manager</option>
                  </select>
                </div>
                <button
                  type="submit"
                  disabled={saving}
                  className="w-full rounded-xl bg-[#1A3F22] px-5 py-3.5 font-semibold text-white transition hover:bg-[#2B5631] disabled:opacity-50"
                >
                  {saving ? 'Creating invitation…' : 'Create invitation'}
                </button>
              </form>

              {inviteLink && (
                <div className="mt-6 rounded-xl border border-border-soft bg-[#F7F9F5] p-4">
                  <p className="text-sm font-semibold">Your invitation link</p>
                  <p className="mt-1 text-xs text-text-muted">
                    Shown only once. Share it privately; it expires after seven days.
                  </p>
                  <input
                    readOnly
                    aria-label="Invitation link"
                    value={inviteLink}
                    onFocus={(event) => event.target.select()}
                    className="mt-3 w-full rounded-lg border border-border-soft bg-white p-3 text-xs"
                  />
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="mt-3 inline-flex items-center gap-2 rounded-lg bg-[#D99201] px-4 py-2.5 text-sm font-bold text-[#1A3F22]"
                  >
                    {copied ? <Check size={16} /> : <ClipboardCopy size={16} />}
                    {copied ? 'Copied' : 'Copy link'}
                  </button>
                </div>
              )}
            </section>
          </div>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-xl font-bold">Invitations</h2>
            <p className="mt-1 text-sm text-text-muted">
              Track invitations and revoke links that are no longer needed.
            </p>

            <div className="mt-6 space-y-3">
              {!loadingTeam && !invitations.length && (
                <div className="rounded-xl bg-[#F7F9F5] p-8 text-center text-sm text-text-muted">
                  No invitations yet. Invite your first teammate above.
                </div>
              )}

              {invitations.map((invitation) => {
                const currentStatus = invitationStatus(invitation)

                return (
                  <div
                    key={invitation.id}
                    className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border-soft p-4"
                  >
                    <div>
                      <p className="font-semibold">{invitation.email}</p>
                      <p className="mt-1 text-sm text-text-muted">
                        {ROLE_LABELS[invitation.role]} · Expires {formatDateTime(invitation.expires_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={
                        currentStatus === 'Accepted'
                          ? 'rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-800'
                          : currentStatus === 'Pending'
                            ? 'rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800'
                            : 'rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600'
                      }>
                        {currentStatus}
                      </span>
                      {currentStatus === 'Pending' && (
                        <button
                          type="button"
                          disabled={revokingId === invitation.id}
                          onClick={() => handleRevoke(invitation.id)}
                          className="inline-flex items-center gap-1 text-sm font-semibold text-red-700 disabled:opacity-50"
                        >
                          <XCircle size={16} />
                          Revoke
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
