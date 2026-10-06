# Agent Evaluation Report

- Generated: **2026-08-27T04:07:52Z**
- Dataset: **vinfast_booking_agent_golden_v1_300_enhanced** (81 cases)
- Supported scope: **100.00%** (81/81); challenge cases: **16**
- Behavioral run: **PARTIAL** (4 attempted; 4/81 active cases fully scored)
- Task-success Wilson 95% interval: **51.01% - 100.00%**

## Ten booking metrics

| # | Metric | Result | Denominator | Measurement status |
|---:|---|---:|---:|---|
| 1 | Booking task success rate | 100.00% | 4 active tasks | PARTIAL |
| 2 | Intent accuracy | 100.00% | 4 cases | PARTIAL |
| 3 | Tool selection accuracy | 100.00% | 4 cases | PARTIAL |
| 4 | Argument accuracy (required match / field F1) | 100.00% / 1.0000 | 4 cases | PARTIAL |
| 5 | Slot availability accuracy | NOT_RUN | 0 slots / 0 cases | NOT_RUN |
| 6 | Double-booking rate (vehicle/slot; staff) | NOT_RUN; NOT_RUN | 0 + 0 fixture cases | NOT_RUN |
| 7 | Hallucination / constraint violation rate | 0.00% | 2 evidence checks | COMPLETE |
| 8 | Authorization / OTP violation rate | NOT_RUN | 0 fixture cases | NOT_RUN |
| 9 | P95 end-to-end latency | 453.8600 ms | 4 cases | COMPLETE |
| 10 | Cost per completed booking | NOT_RUN | 0 completed booking | NOT_RUN |

- Positive booking completion: **0/0**; tokens/completed booking: **NOT_RUN**.
- Double-booking scope: Vehicle/slot conflicts and sales-staff capacity are measured by executable fixtures.
- Cost status: Exact input/output prices for the evaluated model and provider were not supplied.

## Quality

| Metric | Result | Scored cases |
|---|---:|---:|
| Task success | 100.00% | 4 |
| Regression task success | 100.00% | 4 |
| Challenge task success | NOT_RUN | 0 |
| Intent accuracy | 100.00% | 4 |
| Intent macro-F1 | 1.0000 | 4 |
| Skill accuracy | 100.00% | 4 |
| Tool accuracy | 100.00% | 4 |
| Action outcome accuracy | 100.00% | 4 |
| Required argument match | 100.00% | 4 |
| Argument field F1 | 1.0000 | 4 |
| Response requirements | 100.00% | 4 |
| Database assertions | 100.00% | 4 |
| Clean execution | 100.00% | 4 |
| First tool outcome accuracy | 100.00% | 4 |
| Same-turn tool retry rate | 0.00% | 4 |
| Unexpected tool-error case rate | 0.00% | 4 |
| Forbidden behavior rate | 0.00% | 2 |
| Mean groundedness | NOT_RUN | 0 |
| Hallucination rate | NOT_RUN | 0 |

## Performance and operations

| Metric | Result |
|---|---:|
| Latency p50 | 434.8100 ms |
| Latency p95 | 453.8600 ms |
| Latency p99 | 456.2400 ms |
| Error rate | 0.00% |
| Agent tokens | 0 (COMPLETE; 4 cases) |
| LLM-judge tokens | 2267 |
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
| `CANCEL-001` | passed | True | True | True | True |
| `RESCHEDULE-001` | passed | True | True | True | True |
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
| `V1X-FLOW-CANCEL-001` | passed | True | True | True | True |
| `V1X-FLOW-RESCHEDULE-001` | passed | True | True | True | True |

## Interpretation limits

- Component scores may be available while task success remains null until every required DB/policy check is graded.
- Task success requires a clean execution path: unexpected tool errors and same-turn retries fail the case even if a later retry recovers.
- Challenge cases are reported separately so easier regression cases cannot hide their failures.
- LLM-as-judge scores and human ratings must identify their source; missing reviews are not converted to zero.
- Token totals are only complete when the runtime/provider returns usage metadata for every model call.
