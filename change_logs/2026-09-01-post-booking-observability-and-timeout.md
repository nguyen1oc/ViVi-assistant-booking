# Change log

## Post-booking experience

- Added post-booking signal capture for household attendance, multiple drivers,
  and family test-drive priorities.
- Added a background repair path when the conversational model omits a required
  post-booking signal update.
- Extended profile context and the internal booking view to surface the new
  booking-scoped signals without treating them as permanent personal-profile
  facts.
- Refined post-booking guidance and tool guardrails for the advisory flow.

## Agent observability

- Added temporary latency diagnostics around graph invocation, node input
  serialization, classifier preparation, and post-booking LLM preparation.
- Logged message counts and payload character counts so oversized conversational
  context and slow provider calls can be isolated by trace ID.

## Reliability

- Increased the frontend Nginx API proxy connect, send, and read timeouts to
  90 seconds for long-running agent responses.

## Notes

- The new diagnostics are intended for the current investigation and should be
  reviewed before being kept as permanent production logging.
