export const INTERACTION_STATE_VERSION = 1

export const BookingMode = Object.freeze({
  IDLE: 'idle',
  VEHICLE_BROWSE: 'vehicle_browse',
  NEW_BOOKING: 'new_booking',
  MANAGE_BOOKING: 'manage_booking',
})

export const BookingPhase = Object.freeze({
  IDLE: 'idle',
  CHOOSE_VEHICLE: 'choose_vehicle',
  CHOOSE_LOCATION: 'choose_location',
  CHOOSE_SHOWROOM: 'choose_showroom',
  CHOOSE_SLOT: 'choose_slot',
  COLLECT_INFO: 'collect_info',
  REVIEW: 'review',
  SUCCESS: 'success',
  ACCESS_REQUEST: 'access_request',
  ACCESS_VERIFY: 'access_verify',
  BOOKING_LIST: 'booking_list',
  BOOKING_EDIT: 'booking_edit',
  BOOKING_CANCEL_CONFIRM: 'booking_cancel_confirm',
  RESCHEDULE_SHOWROOM: 'reschedule_showroom',
  RESCHEDULE_SLOT: 'reschedule_slot',
  RESCHEDULE_CONFIRM: 'reschedule_confirm',
})

export const InteractionEvent = Object.freeze({
  SET_PHASE: 'SET_PHASE',
  SET_ACTIVE_VIEW: 'SET_ACTIVE_VIEW',
  START_LOOKUP: 'START_LOOKUP',
  ACCESS_REQUESTED: 'ACCESS_REQUESTED',
  ACCESS_VERIFY: 'ACCESS_VERIFY',
  ACCESS_LIST: 'ACCESS_LIST',
  ACCESS_EDIT: 'ACCESS_EDIT',
  ACCESS_CANCEL_CONFIRM: 'ACCESS_CANCEL_CONFIRM',
  CANCEL_ACCESS: 'CANCEL_ACCESS',
  CLOSE_BOOKING_DETAILS: 'CLOSE_BOOKING_DETAILS',
  EXIT_MANAGE_BOOKING: 'EXIT_MANAGE_BOOKING',
  VIEW_VEHICLE: 'VIEW_VEHICLE',
  START_RESCHEDULE: 'START_RESCHEDULE',
  RESCHEDULE_SHOWROOM: 'RESCHEDULE_SHOWROOM',
  RESCHEDULE_SLOT: 'RESCHEDULE_SLOT',
  RESCHEDULE_CONFIRM: 'RESCHEDULE_CONFIRM',
  FINISH_RESCHEDULE: 'FINISH_RESCHEDULE',
})

const LEGACY_PHASES = {
  idle: [BookingMode.IDLE, BookingPhase.IDLE, 'agent'],
  need_car: [BookingMode.VEHICLE_BROWSE, BookingPhase.CHOOSE_VEHICLE, 'agent'],
  need_address: [BookingMode.NEW_BOOKING, BookingPhase.CHOOSE_LOCATION, 'car'],
  need_ward: [BookingMode.NEW_BOOKING, BookingPhase.CHOOSE_LOCATION, 'car'],
  choose_showroom: [BookingMode.NEW_BOOKING, BookingPhase.CHOOSE_SHOWROOM, 'map'],
  choose_slot: [BookingMode.NEW_BOOKING, BookingPhase.CHOOSE_SLOT, 'schedule'],
  collect_info: [BookingMode.NEW_BOOKING, BookingPhase.COLLECT_INFO, 'schedule'],
  review: [BookingMode.NEW_BOOKING, BookingPhase.REVIEW, 'ticket'],
  success: [BookingMode.NEW_BOOKING, BookingPhase.SUCCESS, 'ticket'],
  lookup: [BookingMode.MANAGE_BOOKING, BookingPhase.ACCESS_REQUEST, 'bookings'],
}

const LEGACY_STAGE_BY_PHASE = {
  [BookingPhase.IDLE]: 'idle',
  [BookingPhase.CHOOSE_VEHICLE]: 'need_car',
  [BookingPhase.CHOOSE_LOCATION]: 'need_address',
  [BookingPhase.CHOOSE_SHOWROOM]: 'choose_showroom',
  [BookingPhase.CHOOSE_SLOT]: 'choose_slot',
  [BookingPhase.COLLECT_INFO]: 'collect_info',
  [BookingPhase.REVIEW]: 'review',
  [BookingPhase.SUCCESS]: 'success',
}

const defaultReturnTarget = Object.freeze({
  mode: BookingMode.IDLE,
  phase: BookingPhase.IDLE,
  activeView: 'agent',
})

const lookupReturnTarget = (state) => {
  if (state.phase === BookingPhase.SUCCESS) {
    return { mode: BookingMode.NEW_BOOKING, phase: BookingPhase.CHOOSE_LOCATION, activeView: 'car' }
  }
  return { mode: state.mode, phase: state.phase, activeView: state.activeView }
}

export function createInteractionState({ stage = 'idle', activeView, interaction } = {}) {
  if (interaction?.version === INTERACTION_STATE_VERSION) {
    const restored = validateInteractionState(interaction)
    if (restored.mode === BookingMode.MANAGE_BOOKING) {
      const target = restored.returnTo || defaultReturnTarget
      return createInteractionState({
        stage: LEGACY_STAGE_BY_PHASE[target.phase] || 'idle',
        activeView: target.activeView,
      })
    }
    return restored
  }
  const [mode, phase, defaultView] = LEGACY_PHASES[stage] || LEGACY_PHASES.idle
  return {
    version: INTERACTION_STATE_VERSION,
    mode,
    phase,
    activeView: activeView || defaultView,
    returnTo: null,
    revision: 0,
  }
}

const withRevision = (state, patch) => ({ ...state, ...patch, revision: state.revision + 1 })

const targetForLegacyStage = (stage, activeView) => {
  const [mode, phase, defaultView] = LEGACY_PHASES[stage] || LEGACY_PHASES.idle
  return { mode, phase, activeView: activeView || defaultView }
}

const returnFromManagement = (state) => validateInteractionState({
  ...state,
  ...(state.returnTo || defaultReturnTarget),
  returnTo: null,
  revision: state.revision + 1,
})

export function bookingInteractionReducer(state, event) {
  switch (event.type) {
    case InteractionEvent.SET_PHASE:
      return withRevision(state, {
        ...targetForLegacyStage(event.stage, event.activeView),
        returnTo: event.stage === 'lookup' ? state.returnTo : null,
      })
    case InteractionEvent.SET_ACTIVE_VIEW:
      return withRevision(state, { activeView: event.activeView })
    case InteractionEvent.START_LOOKUP:
      return withRevision(state, {
        mode: BookingMode.MANAGE_BOOKING,
        phase: BookingPhase.ACCESS_REQUEST,
        activeView: 'bookings',
        returnTo: state.mode === BookingMode.MANAGE_BOOKING
          ? state.returnTo
          : lookupReturnTarget(state),
      })
    case InteractionEvent.ACCESS_REQUESTED:
      return withRevision(state, {
        mode: BookingMode.MANAGE_BOOKING,
        phase: BookingPhase.ACCESS_REQUEST,
        activeView: 'bookings',
        returnTo: state.mode === BookingMode.MANAGE_BOOKING
          ? state.returnTo
          : lookupReturnTarget(state),
      })
    case InteractionEvent.ACCESS_VERIFY:
      return withRevision(state, {
        mode: BookingMode.MANAGE_BOOKING,
        phase: BookingPhase.ACCESS_VERIFY,
        activeView: 'bookings',
        returnTo: state.mode === BookingMode.MANAGE_BOOKING
          ? state.returnTo
          : lookupReturnTarget(state),
      })
    case InteractionEvent.ACCESS_LIST:
      return withRevision(state, { mode: BookingMode.MANAGE_BOOKING, phase: BookingPhase.BOOKING_LIST, activeView: 'bookings' })
    case InteractionEvent.ACCESS_EDIT:
      return withRevision(state, { mode: BookingMode.MANAGE_BOOKING, phase: BookingPhase.BOOKING_EDIT, activeView: 'bookings' })
    case InteractionEvent.ACCESS_CANCEL_CONFIRM:
      return withRevision(state, { mode: BookingMode.MANAGE_BOOKING, phase: BookingPhase.BOOKING_CANCEL_CONFIRM, activeView: 'bookings' })
    case InteractionEvent.CANCEL_ACCESS:
    case InteractionEvent.EXIT_MANAGE_BOOKING:
      return returnFromManagement(state)
    case InteractionEvent.CLOSE_BOOKING_DETAILS:
      if (event.hasBookingList) {
        return withRevision(state, { mode: BookingMode.MANAGE_BOOKING, phase: BookingPhase.BOOKING_LIST, activeView: 'bookings' })
      }
      return returnFromManagement(state)
    case InteractionEvent.VIEW_VEHICLE:
      return withRevision(state, {
        mode: BookingMode.NEW_BOOKING,
        phase: BookingPhase.CHOOSE_LOCATION,
        activeView: 'car',
        returnTo: null,
      })
    case InteractionEvent.START_RESCHEDULE:
    case InteractionEvent.RESCHEDULE_SLOT:
      return withRevision(state, { mode: BookingMode.MANAGE_BOOKING, phase: BookingPhase.RESCHEDULE_SLOT, activeView: 'schedule' })
    case InteractionEvent.RESCHEDULE_SHOWROOM:
      return withRevision(state, { mode: BookingMode.MANAGE_BOOKING, phase: BookingPhase.RESCHEDULE_SHOWROOM, activeView: 'bookings' })
    case InteractionEvent.RESCHEDULE_CONFIRM:
      return withRevision(state, { mode: BookingMode.MANAGE_BOOKING, phase: BookingPhase.RESCHEDULE_CONFIRM, activeView: 'bookings' })
    case InteractionEvent.FINISH_RESCHEDULE:
      return returnFromManagement(state)
    default:
      return state
  }
}

export function validateInteractionState(value) {
  const state = { ...createInteractionState(), ...value, version: INTERACTION_STATE_VERSION }
  const knownModes = new Set(Object.values(BookingMode))
  const knownPhases = new Set(Object.values(BookingPhase))
  if (!knownModes.has(state.mode) || !knownPhases.has(state.phase)) return createInteractionState()
  const managementPhases = new Set([
    BookingPhase.ACCESS_REQUEST,
    BookingPhase.ACCESS_VERIFY,
    BookingPhase.BOOKING_LIST,
    BookingPhase.BOOKING_EDIT,
    BookingPhase.BOOKING_CANCEL_CONFIRM,
    BookingPhase.RESCHEDULE_SHOWROOM,
    BookingPhase.RESCHEDULE_SLOT,
    BookingPhase.RESCHEDULE_CONFIRM,
  ])
  if ((state.mode === BookingMode.MANAGE_BOOKING) !== managementPhases.has(state.phase)) return createInteractionState()
  return state
}

export function toLegacyStage(state) {
  return LEGACY_STAGE_BY_PHASE[state.phase] || (state.mode === BookingMode.MANAGE_BOOKING ? 'lookup' : 'idle')
}

export function selectAllowedActions(state, facts = {}) {
  const actions = new Set()
  actions.add('start_lookup')
  if (state.phase === BookingPhase.CHOOSE_VEHICLE) actions.add('choose_vehicle')
  if (state.phase === BookingPhase.CHOOSE_LOCATION) {
    actions.add('use_geolocation')
    actions.add('switch_vehicle')
  }
  if (state.phase === BookingPhase.CHOOSE_SHOWROOM) actions.add('select_showroom')
  if (state.phase === BookingPhase.CHOOSE_SLOT) actions.add('select_slot')
  if ([BookingPhase.ACCESS_REQUEST, BookingPhase.ACCESS_VERIFY].includes(state.phase)) actions.add('cancel_access')
  if (state.phase === BookingPhase.BOOKING_LIST) {
    actions.add('select_booking')
    actions.add('exit_manage_booking')
  }
  if (state.phase === BookingPhase.BOOKING_EDIT) {
    actions.add('close_booking_details')
    if (facts.allowedBookingActions?.includes('update_details')) actions.add('update_details')
    if (facts.allowedBookingActions?.includes('reschedule')) actions.add('reschedule')
  }
  if (state.phase === BookingPhase.RESCHEDULE_CONFIRM) {
    actions.add('close_booking_details')
    if (facts.allowedBookingActions?.includes('update_details')) actions.add('update_details')
    if (facts.allowedBookingActions?.includes('reschedule')) actions.add('confirm_reschedule')
  }
  if (state.phase === BookingPhase.BOOKING_CANCEL_CONFIRM) actions.add('cancel_booking')
  if (state.mode === BookingMode.MANAGE_BOOKING) actions.add('view_vehicle')
  return [...actions]
}

export function selectWorkspace(state) {
  if (state.mode === BookingMode.IDLE || [BookingPhase.ACCESS_REQUEST, BookingPhase.ACCESS_VERIFY].includes(state.phase)) {
    return { visible: false, kind: 'none', activeView: state.activeView }
  }
  if (state.mode === BookingMode.MANAGE_BOOKING) {
    const kind = state.phase.startsWith('reschedule_') ? 'reschedule' : 'bookings'
    return { visible: true, kind, activeView: state.activeView }
  }
  return { visible: true, kind: 'new_booking', activeView: state.activeView }
}

export function selectComposerMode(state) {
  if (state.phase === BookingPhase.ACCESS_REQUEST) return 'access_request'
  if (state.phase === BookingPhase.ACCESS_VERIFY) return 'access_verify'
  if ([BookingPhase.BOOKING_EDIT, BookingPhase.RESCHEDULE_CONFIRM, BookingPhase.RESCHEDULE_SLOT, BookingPhase.RESCHEDULE_SHOWROOM].includes(state.phase)) return 'booking_edit'
  if (state.phase === BookingPhase.COLLECT_INFO) return 'customer_form'
  if (state.phase === BookingPhase.REVIEW) return 'review'
  return 'chat'
}

export function serializeInteractionState(state) {
  return {
    version: INTERACTION_STATE_VERSION,
    mode: state.mode,
    phase: state.phase,
    activeView: state.activeView,
    returnTo: state.returnTo,
    revision: state.revision,
  }
}
