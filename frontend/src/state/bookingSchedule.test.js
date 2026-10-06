import assert from 'node:assert/strict'
import test from 'node:test'
import { calendarRequestForSearch, groupSlots, heldSlotFromResult, mergeAvailability } from './bookingSchedule.js'

const day = (value, slotId) => ({ value, times: [{ slotId, isAvailable: true }] })

const searchResult = {
  search_stage: 'slot_selection', resolved_vehicle: { code: 'VF3', name: 'VinFast VF 3' },
  selected_showroom: { id: '60313' }, slots: [],
}

test('a filtered answer loads the new vehicle calendar without carrying chat filters or limits', () => {
  const request = calendarRequestForSearch({ ...searchResult, focused_date: '2026-09-02' }, {
    vehicle_model: 'VF 3', showroom_id: '60313', preferred_date: '2026-09-02',
    preferred_time: '10:00', slot_limit: 5,
  })
  assert.deepEqual(request, { vehicleModel: 'VF3', showroomId: '60313' })
})

test('single, list and range searches reload full availability even when the answer is empty', () => {
  for (const filter of [
    { focused_date: '2026-09-02' },
    { requested_dates: ['2026-09-02', '2026-09-04'] },
    { requested_date_range: { from: '2026-09-01', to: '2026-09-07' } },
  ]) {
    assert.deepEqual(calendarRequestForSearch({ ...searchResult, ...filter }), {
      vehicleModel: 'VF3', showroomId: '60313',
    })
  }
})

test('older responses without date metadata still load full calendar from structured input', () => {
  assert.ok(calendarRequestForSearch(searchResult, { preferred_date: '2026-09-02' }))
  assert.ok(calendarRequestForSearch(searchResult, { slot_limit: 5 }))
})

test('unfiltered and showroom-selection responses do not trigger a redundant calendar read', () => {
  assert.equal(calendarRequestForSearch(searchResult), null)
  assert.equal(calendarRequestForSearch(searchResult, { preferred_time: '10:00' }), null)
  assert.equal(calendarRequestForSearch({ ...searchResult, search_stage: 'showroom_selection' }, {
    preferred_date: '2026-09-02',
  }), null)
})

test('a complete read restores other days without mixing old vehicle slots or reviving stale slots', () => {
  const partial = mergeAvailability([day('2026-09-01', 'vf9-old')], [day('2026-09-02', 'vf3-now-held')], {
    sameSelection: false, data: { focused_date: '2026-09-02' },
  })
  const complete = [day('2026-09-01', 'vf3-before'), day('2026-09-03', 'vf3-after')]
  assert.deepEqual(mergeAvailability(partial, complete, { sameSelection: true, data: {} }), complete)
})

test('switching vehicle at the same showroom replaces all previous vehicle slots', () => {
  const oldSlots = [day('2026-08-30', 'vf9'), day('2026-09-01', 'vf9-september')]
  const newSlots = [day('2026-08-30', 'vf3')]
  assert.deepEqual(mergeAvailability(oldSlots, newSlots, {
    sameSelection: false, data: { focused_date: '2026-08-30' },
  }), newSlots)
  assert.deepEqual(mergeAvailability(oldSlots, [], {
    sameSelection: false, data: { focused_date: '2026-08-30' },
  }), [])
})

test('empty date results invalidate that date without losing unrelated dates', () => {
  const existing = [day('2026-08-30', 'old'), day('2026-09-01', 'other')]
  assert.deepEqual(mergeAvailability(existing, [], {
    sameSelection: true, data: { focused_date: '2026-08-30' },
  }), [existing[1]])
})

test('range and list searches replace their entire scope, including now-empty dates', () => {
  const existing = [day('2026-08-30', 'keep'), day('2026-09-01', 'old1'), day('2026-09-07', 'old7')]
  for (const data of [
    { requested_date_range: { from: '2026-09-01', to: '2026-09-07' } },
    { requested_dates: ['2026-09-01', '2026-09-07'] },
  ]) {
    assert.deepEqual(mergeAvailability(existing, [day('2026-09-01', 'new')], {
      sameSelection: true, data,
    }), [existing[0], day('2026-09-01', 'new')])
  }
})

test('a full refresh removes stale availability', () => {
  assert.deepEqual(mergeAvailability([day('2026-08-30', 'old')], [], {
    sameSelection: true, data: {},
  }), [])
})

test('held slot metadata builds the ticket without another availability search', () => {
  const held = heldSlotFromResult({
    slot_id: 'vf3-9am', start_at: '2026-08-30T02:00:00Z', end_at: '2026-08-30T02:30:00Z',
  })
  assert.equal(held.slotId, 'vf3-9am')
  assert.equal(held.date, '2026-08-30')
  assert.equal(held.time, '09:00')
  assert.equal(held.durationMinutes, 30)
  assert.equal(held.isAvailable, false)
  assert.equal(heldSlotFromResult({ slot_id: 'legacy' }), null)
})

test('calendar day and time consistently use Vietnam timezone across midnight', () => {
  const [group] = groupSlots([{
    id: 'morning', start_at: '2026-08-29T23:30:00Z', end_at: '2026-08-30T00:00:00Z', status: 'available',
  }])
  assert.equal(group.value, '2026-08-30')
  assert.equal(group.times[0].time, '06:30')
})
