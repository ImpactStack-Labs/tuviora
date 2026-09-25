import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import EventPicker from '../components/EventPicker'
import LoadingRow from '../components/LoadingRow'
import { formatApiError } from '../lib/events'
import {
  createBudgetItem,
  deleteBudgetItem,
  formatMoney,
  getBudgetItems,
  getEventSummary,
  updateBudgetItem,
} from '../lib/finance'

const CATEGORIES = ['venue', 'catering', 'equipment', 'marketing', 'transport', 'staff', 'other']
const EMPTY_ITEM = { category: 'venue', description: '', vendor: '', planned_amount: '', actual_amount: '' }
const INPUT = 'rounded-xl border border-border-soft bg-white px-3 py-2 text-sm outline-none focus:border-[#58761B]'

export default function BudgetPage() {
  const [event, setEvent] = useState(null)
  const [items, setItems] = useState([])
  const [summary, setSummary] = useState(null)
  const [draft, setDraft] = useState(EMPTY_ITEM)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (!event) return
    let active = true
    // Same pattern as sibling pages (e.g. Communications); a loading flag
    // set at the start of a data-fetch effect, not a state sync.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true)

    Promise.all([getBudgetItems(event.id), getEventSummary(event.id)])
      .then(([list, s]) => {
        if (!active) return
        setItems(list)
        setSummary(s)
      })
      .catch((err) => { if (active) setError(formatApiError(err)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [event, refreshKey])

  async function run(action) {
    setSaving(true)
    setError('')
    try {
      await action()
      setRefreshKey((k) => k + 1)
    } catch (err) {
      setError(formatApiError(err))
    } finally {
      setSaving(false)
    }
  }

  function handleAdd(e) {
    e.preventDefault()
    run(async () => {
      await createBudgetItem(event.id, {
        ...draft,
        actual_amount: draft.actual_amount === '' ? null : draft.actual_amount,
      })
      setDraft(EMPTY_ITEM)
    })
  }

  const currency = summary?.currency || 'UGX'
  const money = (v) => formatMoney(v, currency)
  const net = Number(summary?.budget.net || 0)

  return (
    <div className="space-y-8">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58761B]">
          Event finances
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#1A3F22] sm:text-4xl">
          Budget
        </h1>
        <p className="mt-3 max-w-2xl text-text-muted">
          Plan costs, record what was spent and track which vendors are still unpaid.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <EventPicker id="budget-event" value={event} onChange={setEvent} onError={setError} />

      {loading && <LoadingRow />}

      {summary && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            {[
              ['Planned', money(summary.budget.planned)],
              ['Actual spend', money(summary.budget.actual)],
              ['Ticket revenue', money(summary.payments.collected)],
              ['Net', money(summary.budget.net)],
              ['Unpaid vendors', money(summary.budget.unpaid)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
                <p className="text-sm text-text-muted">{label}</p>
                <p className={`mt-2 text-2xl font-bold ${label === 'Net' && net < 0 ? 'text-red-700' : 'text-[#1A3F22]'}`}>
                  {value}
                </p>
              </div>
            ))}
          </div>

          <section className="rounded-2xl border border-border-soft bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-lg font-semibold">Budget lines</h2>

            <form onSubmit={handleAdd} className="mt-4 grid gap-2 md:grid-cols-[auto_1fr_1fr_auto_auto_auto]">
              <select aria-label="Category" value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })} className={INPUT}>
                {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <input aria-label="Description" required placeholder="Description" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} className={INPUT} />
              <input aria-label="Vendor" placeholder="Vendor (optional)" value={draft.vendor} onChange={(e) => setDraft({ ...draft, vendor: e.target.value })} className={INPUT} />
              <input aria-label="Planned amount" required type="number" min="0" step="0.01" placeholder="Planned" value={draft.planned_amount} onChange={(e) => setDraft({ ...draft, planned_amount: e.target.value })} className={INPUT} />
              <input aria-label="Actual amount" type="number" min="0" step="0.01" placeholder="Actual" value={draft.actual_amount} onChange={(e) => setDraft({ ...draft, actual_amount: e.target.value })} className={INPUT} />
              <button type="submit" disabled={saving} className="rounded-xl bg-[#58761B] px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">
                Add
              </button>
            </form>

            {!items.length && <p className="mt-4 text-sm text-text-muted">No budget lines yet.</p>}
            {items.length > 0 && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-text-muted">
                    <tr>
                      <th className="py-2 pr-4">Category</th>
                      <th className="py-2 pr-4">Description</th>
                      <th className="py-2 pr-4">Vendor</th>
                      <th className="py-2 pr-4">Planned</th>
                      <th className="py-2 pr-4">Actual</th>
                      <th className="py-2 pr-4">Paid</th>
                      <th className="py-2"><span className="sr-only">Delete</span></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#EDF1EA]">
                    {items.map((item) => (
                      <tr key={item.id}>
                        <td className="py-2 pr-4">{item.category}</td>
                        <td className="py-2 pr-4">{item.description}</td>
                        <td className="py-2 pr-4">{item.vendor || '—'}</td>
                        <td className="py-2 pr-4">{money(item.planned_amount)}</td>
                        <td className="py-2 pr-4">{item.actual_amount === null ? '—' : money(item.actual_amount)}</td>
                        <td className="py-2 pr-4">
                          <input
                            type="checkbox"
                            aria-label={`Mark ${item.description} paid`}
                            checked={item.paid}
                            disabled={saving}
                            onChange={() => run(() => updateBudgetItem(event.id, item.id, { paid: !item.paid }))}
                          />
                        </td>
                        <td className="py-2">
                          <button
                            type="button"
                            aria-label={`Delete ${item.description}`}
                            disabled={saving}
                            onClick={() => window.confirm('Delete this budget line?') && run(() => deleteBudgetItem(event.id, item.id))}
                            className="text-red-700 disabled:opacity-50"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
