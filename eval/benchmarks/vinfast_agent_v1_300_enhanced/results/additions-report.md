# Agent Evaluation Report

- Generated: **2026-08-25T03:26:47Z**
- Dataset: **vinfast_booking_agent_golden_v1_300_enhanced** (81 cases)
- Supported scope: **100.00%** (81/81); challenge cases: **16**
- Behavioral run: **PARTIAL** (24 attempted; 24/81 active cases fully scored)
- Task-success Wilson 95% interval: **74.15% - 97.68%**

## Ten booking metrics

| # | Metric | Result | Denominator | Measurement status |
|---:|---|---:|---:|---|
| 1 | Booking task success rate | 91.67% | 24 active tasks | PARTIAL |
| 2 | Intent accuracy | 95.83% | 24 cases | PARTIAL |
| 3 | Tool selection accuracy | 100.00% | 24 cases | PARTIAL |
| 4 | Argument accuracy (required match / field F1) | 95.83% / 0.9778 | 24 cases | PARTIAL |
| 5 | Slot availability accuracy | 100.00% | 187 slots / 4 cases | PARTIAL |
| 6 | Double-booking rate (vehicle/slot; staff) | NOT_RUN; NOT_RUN | 0 + 0 fixture cases | NOT_RUN |
| 7 | Hallucination / constraint violation rate | NOT_RUN | 0 evidence checks | NOT_RUN |
| 8 | Authorization / OTP violation rate | NOT_RUN | 0 fixture cases | NOT_RUN |
| 9 | P95 end-to-end latency | 17228.4400 ms | 24 cases | COMPLETE |
| 10 | Cost per completed booking | 0.0000 | 2 completed booking | COMPLETE |

- Positive booking completion: **2/2**; tokens/completed booking: **0.0000**.
- Double-booking scope: Vehicle/slot conflicts and sales-staff capacity are measured by executable fixtures.
- Cost status: Structured booking actions used zero agent-model tokens; infrastructure cost is excluded.

## Quality

| Metric | Result | Scored cases |
|---|---:|---:|
| Task success | 91.67% | 24 |
| Regression task success | 95.00% | 20 |
| Challenge task success | 75.00% | 4 |
| Intent accuracy | 95.83% | 24 |
| Intent macro-F1 | 0.7949 | 24 |
| Skill accuracy | 100.00% | 24 |
| Tool accuracy | 100.00% | 24 |
| Action outcome accuracy | 100.00% | 24 |
| Required argument match | 95.83% | 24 |
| Argument field F1 | 0.9778 | 24 |
| Response requirements | 100.00% | 24 |
| Database assertions | 100.00% | 4 |
| Clean execution | 100.00% | 24 |
| First tool outcome accuracy | 100.00% | 24 |
| Same-turn tool retry rate | 0.00% | 24 |
| Unexpected tool-error case rate | 0.00% | 24 |
| Forbidden behavior rate | NOT_RUN | 0 |
| Mean groundedness | NOT_RUN | 0 |
| Hallucination rate | NOT_RUN | 0 |

## Performance and operations

| Metric | Result |
|---|---:|
| Latency p50 | 10615.0100 ms |
| Latency p95 | 17228.4400 ms |
| Latency p99 | 18352.1400 ms |
| Error rate | 0.00% |
| Agent tokens | 434419 (COMPLETE; 24 cases) |
| LLM-judge tokens | NOT_RUN |
| Estimated cost | 0.0928 |
| Test line coverage | 74.0100% |

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
| `V1X-MT-SEARCH-001` | passed | True | True | True | True |
| `V1X-MT-SEARCH-002` | passed | True | True | True | True |
| `V1X-MT-SEARCH-003` | failed | False | True | True | True |
| `V1X-MT-CORRECT-001` | passed | True | True | True | True |
| `V1X-MT-CORRECT-002` | passed | True | True | True | True |
| `V1X-MT-CORRECT-003` | passed | True | True | True | True |
| `V1X-MT-CORRECT-004` | passed | True | True | True | True |
| `V1X-MT-CODESWITCH-001` | passed | True | True | True | True |
| `V1X-MT-TYPO-001` | passed | True | True | True | True |
| `V1X-MT-DATETIME-001` | passed | True | True | True | True |
| `V1X-MT-DATETIME-002` | passed | True | True | True | True |
| `V1X-MT-DATETIME-003` | failed | True | True | True | True |
| `V1X-GEO-001` | passed | True | True | True | True |
| `V1X-GEO-002` | passed | True | True | True | True |
| `V1X-GEO-003` | passed | True | True | True | True |
| `V1X-GEO-004` | passed | True | True | True | True |
| `V1X-GEO-005` | passed | True | True | True | True |
| `V1X-GEO-006` | passed | True | True | True | True |
| `V1X-GEO-007` | passed | True | True | True | True |
| `V1X-GEO-008` | passed | True | True | True | True |
| `V1X-FLOW-CONFIRM-001` | passed | True | True | True | True |
| `V1X-FLOW-CONFIRM-002` | passed | True | True | True | True |
| `V1X-FLOW-CANCEL-001` | passed | True | True | True | True |
| `V1X-FLOW-RESCHEDULE-001` | passed | True | True | True | True |

## Interpretation limits

- Component scores may be available while task success remains null until every required DB/policy check is graded.
- Task success requires a clean execution path: unexpected tool errors and same-turn retries fail the case even if a later retry recovers.
- Challenge cases are reported separately so easier regression cases cannot hide their failures.
- LLM-as-judge scores and human ratings must identify their source; missing reviews are not converted to zero.
- Token totals are only complete when the runtime/provider returns usage metadata for every model call.
