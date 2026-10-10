
## anthropic/claude-haiku-5-5  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=32  records=32  cost=$0.0153  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | 0.88 | 0 | 0 | 972 | 0.00056 | 4.9 |
| deduce | high | 8 | 1.00 | 0 | 0 | 1746 | 0.00107 | 9.1 |
| arith | none | 8 | 1.00 | 0 | 0 | 156 | 0.00009 | 1.0 |
| arith | high | 8 | 1.00 | 0 | 0 | 296 | 0.00018 | 1.6 |
| distract | none | 0 | - | 0 | 0 | - | - | - |
| distract | high | 0 | - | 0 | 0 | - | - | - |

## anthropic/claude-sonnet-5@default  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=32  records=32  cost=$0.5496  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | 1.00 | 0 | 0 | 2118 | 0.02346 | 21.1 |
| deduce | high | 8 | 1.00 | 0 | 0 | 3252 | 0.04136 | 36.6 |
| arith | none | 8 | 1.00 | 0 | 0 | 148 | 0.00179 | 1.7 |
| arith | high | 8 | 1.00 | 0 | 0 | 157 | 0.00208 | 2.6 |
| distract | none | 0 | - | 0 | 0 | - | - | - |
| distract | high | 0 | - | 0 | 0 | - | - | - |

## google/gemini-3.7-flash  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=32  records=32  cost=$0.2150  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | 1.00 | 0 | 0 | 1374 | 0.00574 | 12.1 |
| deduce | high | 8 | 1.00 | 0 | 0 | 3220 | 0.01537 | 29.5 |
| arith | none | 8 | 1.00 | 0 | 0 | 473 | 0.00189 | 4.4 |
| arith | high | 8 | 1.00 | 0 | 0 | 1074 | 0.00387 | 7.4 |
| distract | none | 0 | - | 0 | 0 | - | - | - |
| distract | high | 0 | - | 0 | 0 | - | - | - |

## openai/gpt-5.4-mini-2026-03-17  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=32  records=32  cost=$0.1048  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | 0.12 | 1 | 0 | 17 | 0.00029 | 0.9 |
| deduce | high | 8 | 1.00 | 0 | 0 | 1576 | 0.01115 | 10.9 |
| arith | none | 8 | 1.00 | 0 | 0 | 130 | 0.00066 | 1.2 |
| arith | high | 8 | 1.00 | 0 | 0 | 204 | 0.00100 | 1.4 |
| distract | none | 0 | - | 0 | 0 | - | - | - |
| distract | high | 0 | - | 0 | 0 | - | - | - |
   format_fail deduce-005/none: out_tok=26.0 tail=...'Tuesday cannot be determined uniquely from the clues given. |  | FINAL ANSWER: cannot be determined'

## openai/gpt-oss-120b  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=32  records=32  cost=$0.0253  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | - | 0 | 8 | - | - | 0.3 |
   ERROR (deduce/none): BadRequestError: Error code: 400 - {'code': '', 'message': '[{"error":{"code":400,"message":"Expected \'reasoning_effort\' to be one of: \'high\', \'low\', \'max\', \'medium\', \'minimal\'; found \'none\'.","status":"INVALID_ARGUMENT"}}]', 'param': '', 'type': 'invalid_request_error'}
| deduce | high | 8 | 1.00 | 0 | 0 | 5872 | 0.00280 | 69.0 |
| arith | none | 8 | - | 0 | 8 | - | - | 1.1 |
   ERROR (arith/none): BadRequestError: Error code: 400 - {'code': '', 'message': '[{"error":{"code":400,"message":"Expected \'reasoning_effort\' to be one of: \'high\', \'low\', \'max\', \'medium\', \'minimal\'; found \'none\'.","status":"INVALID_ARGUMENT"}}]', 'param': '', 'type': 'invalid_request_error'}
| arith | high | 8 | 0.88 | 0 | 0 | 564 | 0.00036 | 92.1 |
| distract | none | 0 | - | 0 | 0 | - | - | - |
| distract | high | 0 | - | 0 | 0 | - | - | - |

TOTAL cost across downloaded runs: $0.9099

## Difficulty (none level, median across models)
deduce: per-model [0.88, 1.0, 1.0, 0.12] median=0.94
arith: per-model [1.0, 1.0, 1.0, 1.0] median=1.00
distract: per-model [] median=-

## Main-run projection (4 levels; medium/low ~ mean of none and high)
| model | c_none | c_high | 60xR3 | 60xR2 | 45xR3 | 45xR2 |
|---|---|---|---|---|---|---|
| anthropic/claude-haiku-5-5 | 0.00033 | 0.00062 | $0.34 | $0.23 | $0.26 | $0.17 |
| anthropic/claude-sonnet-5@default | 0.01263 | 0.02172 | $12.37 | $8.24 | $9.27 | $6.18 |
| google/gemini-3.7-flash | 0.00382 | 0.00962 | $4.84 | $3.22 | $3.63 | $2.42 |
| openai/gpt-5.4-mini-2026-03-17 | 0.00047 | 0.00608 | $2.36 | $1.57 | $1.77 | $1.18 |
| openai/gpt-oss-120b | None | 0.001579876875 | - | - | - | - |
| **total** | | | $19.90 | $13.27 | $14.93 | $9.95 |
