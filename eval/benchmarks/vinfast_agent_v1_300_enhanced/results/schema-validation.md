# Agent Evaluation Report

- Generated: **2026-08-25T03:09:17Z**
- Dataset: **vinfast_booking_agent_golden_v1_300_enhanced** (81 cases)
- Supported scope: **100.00%** (81/81); challenge cases: **16**
- Behavioral run: **NOT_RUN** (0 attempted; 0/81 active cases fully scored)
- Task-success Wilson 95% interval: **NOT_RUN**

## Ten booking metrics

| # | Metric | Result | Denominator | Measurement status |
|---:|---|---:|---:|---|
| 1 | Booking task success rate | NOT_RUN | 0 active tasks | NOT_RUN |
| 2 | Intent accuracy | NOT_RUN | 0 cases | PARTIAL |
| 3 | Tool selection accuracy | NOT_RUN | 0 cases | PARTIAL |
| 4 | Argument accuracy (required match / field F1) | NOT_RUN / NOT_RUN | 0 cases | PARTIAL |
| 5 | Slot availability accuracy | NOT_RUN | 0 slots / 0 cases | NOT_RUN |
| 6 | Double-booking rate (vehicle/slot; staff) | NOT_RUN; NOT_RUN | 0 + 0 fixture cases | NOT_RUN |
| 7 | Hallucination / constraint violation rate | NOT_RUN | 0 evidence checks | NOT_RUN |
| 8 | Authorization / OTP violation rate | NOT_RUN | 0 fixture cases | NOT_RUN |
| 9 | P95 end-to-end latency | NOT_RUN ms | 0 cases | PARTIAL |
| 10 | Cost per completed booking | NOT_RUN | 0 completed booking | NOT_RUN |

- Positive booking completion: **0/0**; tokens/completed booking: **NOT_RUN**.
- Double-booking scope: Vehicle/slot conflicts and sales-staff capacity are measured by executable fixtures.
- Cost status: Exact input/output prices for the evaluated model and provider were not supplied.

## Quality

| Metric | Result | Scored cases |
|---|---:|---:|
| Task success | NOT_RUN | 0 |
| Regression task success | NOT_RUN | 0 |
| Challenge task success | NOT_RUN | 0 |
| Intent accuracy | NOT_RUN | 0 |
| Intent macro-F1 | NOT_RUN | 0 |
| Skill accuracy | NOT_RUN | 0 |
| Tool accuracy | NOT_RUN | 0 |
| Action outcome accuracy | NOT_RUN | 0 |
| Required argument match | NOT_RUN | 0 |
| Argument field F1 | NOT_RUN | 0 |
| Response requirements | NOT_RUN | 0 |
| Database assertions | NOT_RUN | 0 |
| Clean execution | NOT_RUN | 0 |
| First tool outcome accuracy | NOT_RUN | 0 |
| Same-turn tool retry rate | NOT_RUN | 0 |
| Unexpected tool-error case rate | NOT_RUN | 0 |
| Forbidden behavior rate | NOT_RUN | 0 |
| Mean groundedness | NOT_RUN | 0 |
| Hallucination rate | NOT_RUN | 0 |

## Performance and operations

| Metric | Result |
|---|---:|
| Latency p50 | NOT_RUN ms |
| Latency p95 | NOT_RUN ms |
| Latency p99 | NOT_RUN ms |
| Error rate | NOT_RUN |
| Agent tokens | NOT_RUN (NOT_RUN; 0 cases) |
| LLM-judge tokens | NOT_RUN |
| Estimated cost | NOT_RUN |
| Test line coverage | NOT_RUN% |

## Security and human evaluation

- Negative-case outcome accuracy: **NOT_RUN** (0/16).
- Human review: **NOT_RUN**; case coverage NOT_RUN.
- Human task success: **NOT_RUN**.
- Satisfaction: **NOT_RUN/5**; CSAT 4–5: **NOT_RUN**.

## Case status

| Case | Status | Intent | Skill | Tool | Clean execution |
|---|---|---:|---:|---:|---:|
| `SEARCH-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFLICT-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD_EXPIRED-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `OTP_BAD-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `OTP_EXPIRED-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CANCEL-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `RESCHEDULE-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `INJECTION-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `PII-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `SEARCH-002` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-002` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `SEARCH-003` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-003` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `SEARCH-004` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-004` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `SEARCH-005` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-005` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `SEARCH-006` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-006` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `SEARCH-007` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-007` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `SEARCH-008` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-008` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `SEARCH-009` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-009` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `SEARCH-010` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HOLD-010` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `MODEL-NOT-IN-SHOWROOM-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `MODEL-UNSUPPORTED-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `STAFF-CAPACITY-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `BOOK-FOR-OTHER-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `MULTITURN-SEARCH-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `ACCESS-REQUEST-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `ACCESS-DETAILS-MULTITURN-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-INJECTION-MIXED-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-INJECTION-ROLE-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-INJECTION-ENCODED-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-PII-AUTHORITY-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-BENIGN-QUOTE-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-BENIGN-NEGATION-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-SEARCH-TYPO-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-SEARCH-CORRECTION-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-SEARCH-DATETIME-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-SEARCH-CODE-SWITCH-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-MULTITURN-CORRECTION-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `HARD-SHOWROOM-NOTFOUND-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-E2E-002` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-E2E-003` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-E2E-004` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-E2E-005` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-E2E-006` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-E2E-007` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-E2E-008` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-E2E-009` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `CONFIRM-E2E-010` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-SEARCH-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-SEARCH-002` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-SEARCH-003` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-CORRECT-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-CORRECT-002` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-CORRECT-003` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-CORRECT-004` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-CODESWITCH-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-TYPO-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-DATETIME-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-DATETIME-002` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-MT-DATETIME-003` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-GEO-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-GEO-002` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-GEO-003` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-GEO-004` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-GEO-005` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-GEO-006` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-GEO-007` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-GEO-008` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-FLOW-CONFIRM-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-FLOW-CONFIRM-002` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-FLOW-CANCEL-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| `V1X-FLOW-RESCHEDULE-001` | not_run | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

## Interpretation limits

- Component scores may be available while task success remains null until every required DB/policy check is graded.
- Task success requires a clean execution path: unexpected tool errors and same-turn retries fail the case even if a later retry recovers.
- Challenge cases are reported separately so easier regression cases cannot hide their failures.
- LLM-as-judge scores and human ratings must identify their source; missing reviews are not converted to zero.
- Token totals are only complete when the runtime/provider returns usage metadata for every model call.
