
## anthropic/claude-haiku-5-5  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=52  records=52  cost=$0.0098  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | 1.00 | 0 | 0 | 462 | 0.00026 | 2.4 |
| deduce | high | 8 | 1.00 | 0 | 0 | 711 | 0.00042 | 3.4 |
| arith | none | 8 | 1.00 | 0 | 0 | 126 | 0.00008 | 0.8 |
| arith | high | 8 | 1.00 | 0 | 0 | 258 | 0.00015 | 1.3 |
| distract | none | 8 | 1.00 | 0 | 0 | 76 | 0.00006 | 0.8 |
| distract | high | 8 | 1.00 | 0 | 0 | 134 | 0.00009 | 1.1 |
   cache probe deduce-000: probe1==probe2 False; probe1==main False; lens main/p1/p2 [853, 705, 672]
   cache probe deduce-001: probe1==probe2 False; probe1==main False; lens main/p1/p2 [1265, 1203, 1683]

## anthropic/claude-sonnet-5@default  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=52  records=52  cost=$0.2032  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | 1.00 | 0 | 0 | 429 | 0.00661 | 6.0 |
| deduce | high | 8 | 1.00 | 0 | 0 | 493 | 0.00784 | 6.6 |
| arith | none | 8 | 1.00 | 0 | 0 | 111 | 0.00134 | 1.6 |
| arith | high | 8 | 1.00 | 0 | 0 | 167 | 0.00168 | 1.8 |
| distract | none | 8 | 1.00 | 0 | 0 | 92 | 0.00119 | 1.4 |
| distract | high | 8 | 0.88 | 0 | 0 | 160 | 0.00222 | 2.4 |
   cache probe deduce-000: probe1==probe2 False; probe1==main False; lens main/p1/p2 [772, 731, 844]
   cache probe deduce-001: probe1==probe2 False; probe1==main False; lens main/p1/p2 [3745, 2495, 2066]

## google/gemini-3.7-flash  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=52  records=52  cost=$0.1082  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | 1.00 | 0 | 0 | 366 | 0.00162 | 4.8 |
| deduce | high | 8 | 1.00 | 0 | 0 | 822 | 0.00436 | 9.9 |
| arith | none | 8 | 1.00 | 0 | 0 | 332 | 0.00120 | 3.8 |
| arith | high | 8 | 1.00 | 0 | 0 | 745 | 0.00335 | 6.9 |
| distract | none | 8 | 1.00 | 0 | 0 | 86 | 0.00042 | 2.3 |
| distract | high | 8 | 1.00 | 0 | 0 | 341 | 0.00160 | 4.7 |
   cache probe deduce-000: probe1==probe2 True; probe1==main True; lens main/p1/p2 [17, 17, 17]
   cache probe deduce-001: probe1==probe2 True; probe1==main True; lens main/p1/p2 [17, 17, 17]

## google/gemini-3.8-flash  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=52  records=52  cost=$0.1137  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | 1.00 | 0 | 0 | 390 | 0.00179 | 4.2 |
| deduce | high | 8 | 1.00 | 0 | 0 | 780 | 0.00477 | 9.4 |
| arith | none | 8 | 1.00 | 0 | 0 | 354 | 0.00126 | 3.3 |
| arith | high | 8 | 1.00 | 0 | 0 | 800 | 0.00345 | 6.9 |
| distract | none | 8 | 1.00 | 0 | 0 | 84 | 0.00040 | 1.8 |
| distract | high | 8 | 1.00 | 0 | 0 | 343 | 0.00166 | 4.1 |
   cache probe deduce-000: probe1==probe2 True; probe1==main True; lens main/p1/p2 [17, 17, 17]
   cache probe deduce-001: probe1==probe2 True; probe1==main True; lens main/p1/p2 [17, 17, 17]

## openai/gpt-5.4-mini-2026-03-17  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=52  records=52  cost=$0.0402  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | 0.25 | 0 | 0 | 17 | 0.00031 | 1.1 |
| deduce | high | 8 | 1.00 | 0 | 0 | 415 | 0.00250 | 4.2 |
| arith | none | 8 | 1.00 | 0 | 0 | 91 | 0.00048 | 1.3 |
| arith | high | 8 | 1.00 | 0 | 0 | 166 | 0.00081 | 1.6 |
| distract | none | 8 | 0.75 | 0 | 0 | 17 | 0.00015 | 0.9 |
| distract | high | 8 | 1.00 | 0 | 0 | 82 | 0.00069 | 1.5 |
   cache probe deduce-000: probe1==probe2 True; probe1==main True; lens main/p1/p2 [22, 22, 22]
   cache probe deduce-001: probe1==probe2 True; probe1==main False; lens main/p1/p2 [44, 22, 22]

## openai/gpt-oss-120b  state=BENCHMARK_TASK_RUN_STATE_COMPLETED  subruns=52  records=52  cost=$0.0125  caching=['False']
| family | level | n | acc | format_fail | api_error | median out tok | mean cost | mean latency s |
|---|---|---|---|---|---|---|---|---|
| deduce | none | 8 | - | 0 | 8 | - | - | 11.1 |
   ERROR (deduce/none): BadRequestError: Error code: 400 - {'code': '', 'message': '[{"error":{"code":400,"message":"Expected \'reasoning_effort\' to be one of: \'high\', \'low\', \'max\', \'medium\', \'minimal\'; found \'none\'.","status":"INVALID_ARGUMENT"}}]', 'param': '', 'type': 'invalid_request_error'}
| deduce | high | 8 | 0.75 | 2 | 0 | 1130 | 0.00073 | 55.0 |
| arith | none | 8 | - | 0 | 8 | - | - | 2.3 |
   ERROR (arith/none): BadRequestError: Error code: 400 - {'code': '', 'message': '[{"error":{"code":400,"message":"Expected \'reasoning_effort\' to be one of: \'high\', \'low\', \'max\', \'medium\', \'minimal\'; found \'none\'.","status":"INVALID_ARGUMENT"}}]', 'param': '', 'type': 'invalid_request_error'}
| arith | high | 8 | 1.00 | 0 | 0 | 500 | 0.00020 | 73.3 |
| distract | none | 8 | - | 0 | 8 | - | - | 25.9 |
   ERROR (distract/none): BadRequestError: Error code: 400 - {'code': '', 'message': '[{"error":{"code":400,"message":"Expected \'reasoning_effort\' to be one of: \'high\', \'low\', \'max\', \'medium\', \'minimal\'; found \'none\'.","status":"INVALID_ARGUMENT"}}]', 'param': '', 'type': 'invalid_request_error'}
| distract | high | 8 | 0.38 | 2 | 0 | 1654 | 0.00064 | 60.0 |
   cache probe deduce-000: probe1==probe2 True; probe1==main True; lens main/p1/p2 [0, 0, 0]
   cache probe deduce-001: probe1==probe2 True; probe1==main True; lens main/p1/p2 [0, 0, 0]
   format_fail deduce-000/high: out_tok=1173.0 tail=...'Ben |  | FINAL ANSWER:'
   format_fail deduce-003/high: out_tok=1042.0 tail=...'Gus | FINAL ANSWER:'
   format_fail distract-001/high: out_tok=655.0 tail=...'The statement clearly says you have a banana, a mango, and a pear – that’s three fruits. |  | FINAL ANSWER:'
   format_fail distract-002/high: out_tok=1287.0 tail=...' as being in your possession are the drill, wrench, saw, level, and hammer. That’s a total of five tools. |  | FINAL ANSWER:'

TOTAL cost across downloaded runs: $0.4876

## Difficulty (none level, median across models)
deduce: per-model [1.0, 1.0, 1.0, 1.0, 0.25] median=1.00
arith: per-model [1.0, 1.0, 1.0, 1.0, 1.0] median=1.00
distract: per-model [1.0, 1.0, 1.0, 1.0, 0.75] median=1.00

## Main-run projection (4 levels; medium/low ~ mean of none and high)
| model | c_none | c_high | 60xR3 | 60xR2 | 45xR3 | 45xR2 |
|---|---|---|---|---|---|---|
| anthropic/claude-haiku-5-5 | 0.00013 | 0.00022 | $0.13 | $0.08 | $0.09 | $0.06 |
| anthropic/claude-sonnet-5@default | 0.00305 | 0.00392 | $2.51 | $1.67 | $1.88 | $1.25 |
| google/gemini-3.7-flash | 0.00108 | 0.00310 | $1.51 | $1.00 | $1.13 | $0.75 |
| google/gemini-3.8-flash | 0.00115 | 0.00329 | $1.60 | $1.07 | $1.20 | $0.80 |
| openai/gpt-5.4-mini-2026-03-17 | 0.00031 | 0.00133 | $0.59 | $0.39 | $0.44 | $0.30 |
| openai/gpt-oss-120b | None | 0.00052270125 | - | - | - | - |
| **total** | | | $6.33 | $4.22 | $4.75 | $3.17 |
