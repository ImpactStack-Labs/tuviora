// Runnable regression check for format.js — no test framework in this repo.
// Run: node src/lib/format.check.mjs
import assert from 'node:assert/strict'
import { formatEventDate, formatEventTime, formatDateTime } from './format.js'

// formatEventDate: same calendar date regardless of parsing, no off-by-one
// across the UTC boundary that caused the original bug.
assert.equal(formatEventDate('2026-01-15'), '15 January 2026')
assert.equal(formatEventDate('2026-12-31'), '31 December 2026')
assert.equal(formatEventDate(''), 'Date not set')
assert.equal(formatEventDate(null), 'Date not set')
assert.equal(formatEventDate('not-a-date'), 'not-a-date')

// formatEventTime: 24h "HH:MM" -> 12h with AM/PM, invalid input passed through.
assert.equal(formatEventTime('09:05'), '9:05 AM')
assert.equal(formatEventTime('00:00'), '12:00 AM')
assert.equal(formatEventTime('12:00'), '12:00 PM')
assert.equal(formatEventTime('23:59'), '11:59 PM')
assert.equal(formatEventTime(''), 'Not set')
assert.equal(formatEventTime('25:00'), '25:00')

// formatDateTime: real ISO timestamps, shown in viewer's local time.
assert.equal(formatDateTime('2026-01-15T00:00:00Z') !== 'Not set', true)
assert.equal(formatDateTime(''), 'Not set')
assert.equal(formatDateTime('garbage'), 'garbage')

console.log('format.js: all checks passed')
