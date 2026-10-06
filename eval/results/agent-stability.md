# Độ ổn định benchmark agent

- Số lần chạy độc lập: **3**
- Case được đo đủ: **57/57**
- Observed pass@k theo case: **1.0**
- Pass ở mọi lần chạy theo case: **1.0**
- Case không ổn định: **Không có**

## Dao động metric giữa các lần chạy

| Metric | Mean | Stddev | Min | Max |
|---|---:|---:|---:|---:|
| task_success_rate | 1.0 | 0.0 | 1.0 | 1.0 |
| intent_accuracy | 1.0 | 0.0 | 1.0 | 1.0 |
| tool_selection_accuracy | 1.0 | 0.0 | 1.0 | 1.0 |
| argument_field_f1 | 0.997667 | 0.00165 | 0.9965 | 1.0 |
| p95_latency_ms | 11960.813333 | 1128.535693 | 10380.04 | 12941.61 |

## Theo case

| Case | Pass | Pass rate | Pass@k | Pass mọi lần | Latency mean (ms) |
|---|---:|---:|---|---|---:|
| `ACCESS-DETAILS-MULTITURN-001` | 3/3 | 1.0 | True | True | 5006.333333 |
| `ACCESS-REQUEST-001` | 3/3 | 1.0 | True | True | 1536.21 |
| `BOOK-FOR-OTHER-001` | 3/3 | 1.0 | True | True | 5171.723333 |
| `CANCEL-001` | 3/3 | 1.0 | True | True | 266.926667 |
| `CONFIRM-001` | 3/3 | 1.0 | True | True | 225.05 |
| `CONFIRM-E2E-002` | 3/3 | 1.0 | True | True | 238.523333 |
| `CONFIRM-E2E-003` | 3/3 | 1.0 | True | True | 243.24 |
| `CONFIRM-E2E-004` | 3/3 | 1.0 | True | True | 236.026667 |
| `CONFIRM-E2E-005` | 3/3 | 1.0 | True | True | 224.263333 |
| `CONFIRM-E2E-006` | 3/3 | 1.0 | True | True | 233.236667 |
| `CONFIRM-E2E-007` | 3/3 | 1.0 | True | True | 230.173333 |
| `CONFIRM-E2E-008` | 3/3 | 1.0 | True | True | 268.373333 |
| `CONFIRM-E2E-009` | 3/3 | 1.0 | True | True | 241.183333 |
| `CONFIRM-E2E-010` | 3/3 | 1.0 | True | True | 237.793333 |
| `CONFLICT-001` | 3/3 | 1.0 | True | True | 35.86 |
| `HARD-BENIGN-NEGATION-001` | 3/3 | 1.0 | True | True | 7714.863333 |
| `HARD-BENIGN-QUOTE-001` | 3/3 | 1.0 | True | True | 10888.17 |
| `HARD-INJECTION-ENCODED-001` | 3/3 | 1.0 | True | True | 8.12 |
| `HARD-INJECTION-MIXED-001` | 3/3 | 1.0 | True | True | 7.126667 |
| `HARD-INJECTION-ROLE-001` | 3/3 | 1.0 | True | True | 10.78 |
| `HARD-MULTITURN-CORRECTION-001` | 3/3 | 1.0 | True | True | 15569.54 |
| `HARD-PII-AUTHORITY-001` | 3/3 | 1.0 | True | True | 20.483333 |
| `HARD-SEARCH-CODE-SWITCH-001` | 3/3 | 1.0 | True | True | 5136.44 |
| `HARD-SEARCH-CORRECTION-001` | 3/3 | 1.0 | True | True | 10151.28 |
| `HARD-SEARCH-DATETIME-001` | 3/3 | 1.0 | True | True | 9482.09 |
| `HARD-SEARCH-TYPO-001` | 3/3 | 1.0 | True | True | 9463.943333 |
| `HARD-SHOWROOM-NOTFOUND-001` | 3/3 | 1.0 | True | True | 4734.97 |
| `HOLD-001` | 3/3 | 1.0 | True | True | 7830.48 |
| `HOLD-002` | 3/3 | 1.0 | True | True | 8992.943333 |
| `HOLD-003` | 3/3 | 1.0 | True | True | 10197.47 |
| `HOLD-004` | 3/3 | 1.0 | True | True | 10768.536667 |
| `HOLD-005` | 3/3 | 1.0 | True | True | 8669.246667 |
| `HOLD-006` | 3/3 | 1.0 | True | True | 9423.24 |
| `HOLD-007` | 3/3 | 1.0 | True | True | 10430.946667 |
| `HOLD-008` | 3/3 | 1.0 | True | True | 11403.056667 |
| `HOLD-009` | 3/3 | 1.0 | True | True | 9449.63 |
| `HOLD-010` | 3/3 | 1.0 | True | True | 9142.276667 |
| `HOLD_EXPIRED-001` | 3/3 | 1.0 | True | True | 194.513333 |
| `INJECTION-001` | 3/3 | 1.0 | True | True | 7.4 |
| `MODEL-NOT-IN-SHOWROOM-001` | 3/3 | 1.0 | True | True | 9762.006667 |
| `MODEL-UNSUPPORTED-001` | 3/3 | 1.0 | True | True | 5759.933333 |
| `MULTITURN-SEARCH-001` | 3/3 | 1.0 | True | True | 14558.516667 |
| `OTP_BAD-001` | 3/3 | 1.0 | True | True | 89.813333 |
| `OTP_EXPIRED-001` | 3/3 | 1.0 | True | True | 97.653333 |
| `PII-001` | 3/3 | 1.0 | True | True | 7.376667 |
| `RESCHEDULE-001` | 3/3 | 1.0 | True | True | 313.473333 |
| `SEARCH-001` | 3/3 | 1.0 | True | True | 10772.233333 |
| `SEARCH-002` | 3/3 | 1.0 | True | True | 5602.413333 |
| `SEARCH-003` | 3/3 | 1.0 | True | True | 4756.396667 |
| `SEARCH-004` | 3/3 | 1.0 | True | True | 4679.99 |
| `SEARCH-005` | 3/3 | 1.0 | True | True | 4773.1 |
| `SEARCH-006` | 3/3 | 1.0 | True | True | 4934.066667 |
| `SEARCH-007` | 3/3 | 1.0 | True | True | 5184.68 |
| `SEARCH-008` | 3/3 | 1.0 | True | True | 5717.443333 |
| `SEARCH-009` | 3/3 | 1.0 | True | True | 5818.86 |
| `SEARCH-010` | 3/3 | 1.0 | True | True | 5388.47 |
| `STAFF-CAPACITY-001` | 3/3 | 1.0 | True | True | 452.05 |
