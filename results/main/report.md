| model | level | family | n | acc | format_fail | api_error | median out tok | mean $/call |
|---|---|---|---|---|---|---|---|---|
| google/gemini-3.7-flash | none | deduce | 40 | 1.00 | 0 | 0 | 1340 | 0.00581 |
| google/gemini-3.7-flash | none | arith | 40 | 1.00 | 0 | 0 | 453 | 0.00168 |
| google/gemini-3.7-flash | none | distract | 40 | 1.00 | 0 | 0 | 89 | 0.00045 |
| google/gemini-3.7-flash | low | deduce | 40 | 1.00 | 0 | 0 | 1418 | 0.00610 |
| google/gemini-3.7-flash | low | arith | 40 | 1.00 | 0 | 0 | 446 | 0.00171 |
| google/gemini-3.7-flash | low | distract | 40 | 1.00 | 0 | 0 | 94 | 0.00045 |
| google/gemini-3.7-flash | medium | deduce | 40 | 1.00 | 0 | 0 | 2390 | 0.00928 |
| google/gemini-3.7-flash | medium | arith | 40 | 1.00 | 0 | 0 | 566 | 0.00232 |
| google/gemini-3.7-flash | medium | distract | 40 | 1.00 | 0 | 0 | 160 | 0.00076 |
| google/gemini-3.7-flash | high | deduce | 40 | 1.00 | 0 | 0 | 4214 | 0.01683 |
| google/gemini-3.7-flash | high | arith | 40 | 1.00 | 0 | 0 | 1009 | 0.00397 |
| google/gemini-3.7-flash | high | distract | 40 | 1.00 | 0 | 0 | 284 | 0.00152 |
| openai/gpt-oss-120b | low | deduce | 40 | 0.80 | 1 | 0 | 1008 | 0.00047 |
| openai/gpt-oss-120b | low | arith | 40 | 0.93 | 0 | 0 | 292 | 0.00012 |
| openai/gpt-oss-120b | low | distract | 40 | 0.75 | 1 | 0 | 52 | 0.00004 |
| openai/gpt-oss-120b | medium | deduce | 40 | 1.00 | 0 | 0 | 3360 | 0.00126 |
| openai/gpt-oss-120b | medium | arith | 40 | 0.93 | 1 | 0 | 396 | 0.00016 |
| openai/gpt-oss-120b | medium | distract | 40 | 0.60 | 2 | 0 | 238 | 0.00012 |
| openai/gpt-oss-120b | high | deduce | 40 | 0.97 | 1 | 0 | 8058 | 0.00308 |
| openai/gpt-oss-120b | high | arith | 40 | 0.93 | 2 | 0 | 736 | 0.00031 |
| openai/gpt-oss-120b | high | distract | 40 | 0.68 | 1 | 0 | 1082 | 0.00102 |

google/gemini-3.7-flash dial-none: state=COMPLETED subruns=120 records=120 unique(item,repeat)=120 dupes=0 levels=['none'] score=1.0 cost=$0.3173
google/gemini-3.7-flash dial-low: state=COMPLETED subruns=120 records=120 unique(item,repeat)=120 dupes=0 levels=['low'] score=1.0 cost=$0.3303
google/gemini-3.7-flash dial-medium: state=COMPLETED subruns=120 records=120 unique(item,repeat)=120 dupes=0 levels=['medium'] score=1.0 cost=$0.4941
google/gemini-3.7-flash dial-high: state=COMPLETED subruns=120 records=120 unique(item,repeat)=120 dupes=0 levels=['high'] score=1.0 cost=$0.8924
openai/gpt-oss-120b dial-low: state=COMPLETED subruns=120 records=120 unique(item,repeat)=120 dupes=0 levels=['low'] score=0.825 cost=$0.0253
openai/gpt-oss-120b dial-medium: state=COMPLETED subruns=120 records=120 unique(item,repeat)=120 dupes=0 levels=['medium'] score=0.8416666666666667 cost=$0.0618
openai/gpt-oss-120b dial-high: state=COMPLETED subruns=120 records=120 unique(item,repeat)=120 dupes=0 levels=['high'] score=0.8583333333333333 cost=$0.1763

TOTAL cost in results/main: $2.2976
