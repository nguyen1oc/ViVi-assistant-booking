# Trusted Knowledge Pack — Provenance & Review Guide

Generated: 2026-08-19

## File
`post_booking_trusted_knowledge.json`

## Included
- Current official VinFast test-drive preparation requirements.
- Generic EV charging/range guidance from VinFast and U.S. DOE AFDC.
- Generic ADAS and child-seat safety guidance from NHTSA.
- Scoped product facts for VF 3, VF 5, VF 6, VF 7, VF 8 The All New 2026 and VF 9.
- Current VinFast warranty groupings.
- Explicit boundary entries requiring live service data for booking/showroom state.

## Review state
Every crawled entry is `source_verified` but `pending_internal_review`. This means the source was checked during research, but the content has not been approved by your internal/VinFast content owner. A strict production gate should only serve entries whose `review_status` is later changed to `approved`.

## Retrieval rules
1. Filter market first.
2. Filter exact model for vehicle facts.
3. If `trims` is non-empty and trim is known, require trim match.
4. If `model_years` is non-empty and model year is known, require model-year match.
5. Never silently treat `VF 8` and `VF 8 The All New` as identical.
6. Suppress high-time-sensitivity entries after `next_review_date` until refreshed.
7. Never answer current booking/showroom/slot state from this JSON.

## Conflict rule
When two VinFast pages disagree, prefer the current centralized policy page for warranty/policy and the current product page/FAQ for model/trim equipment. Preserve the narrower scope and do not merge conflicting values. During this research, older VinFast FAQ/blog content was found to differ from the current centralized warranty page for VF 7; the JSON therefore uses the centralized current policy.

## Suggested review statuses
- `pending_internal_review`
- `approved`
- `rejected`
- `superseded`
- `expired`
