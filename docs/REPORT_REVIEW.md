# Review of "CloudServe FDE Capstone — Complete Project Report"

Findings are from the report text only. Items marked (code) are handled in this codebase.

## High priority

| # | Section | Issue | Fix |
|---|---|---|---|
| 1 | §9, §28 | Routing accuracy 40% with 100% escalation implies 48 of 80 were expected AUTO and all were escalated (48 false escalations). This is never stated. | State the expected AUTO/ESCALATE split and false escalations next to the 40%. (code: `routing()`) |
| 2 | §28 | Mean runtime 0.4716 s is higher than P95 0.1697 s. This means a few extreme outliers, likely model load or a cold cache. | Report steady-state latency with warm-up excluded, plus max. (code: `latency()`) |
| 3 | §4, header | Validation size is given as 80, and the report notes that other documents say 100 or 120. | Fix one number for this report, and state that the harness is size-agnostic. |
| 4 | §3 A7, §30 | No count of guardrail blocks on any run, so "demonstrably blocks" is claimed but not shown. | Add blocks per guardrail from a real run. (code: harness `guardrails` section) |
| 5 | §21, §23 | "Textual grounding 100%" and "unsupported claims 0" sit beside a human-review 2% hallucination rate. | Label grounding as a lexical/automated check, and state that it is a different measure from human hallucination review. |
| 6 | §17, §19, §11 | "False autos: 27", "18 false automatic responses" and "False escalations: 234" have no denominators. | Give n for each (e.g. 27 of 168 AUTO; 234 of N expected AUTO). |
| 7 | §7 | P@1 (90.57%) is higher than R@1 (76.42%). This only makes sense if tickets have more than one expected doc. | Define R@k (micro over expected docs?) and give the expected-doc total. 76.42% ≈ 81/106 suggests 106 expected docs over 53 tickets. |
| 8 | §30 | "Fairness gate NOT PROVEN" gives no subgroups and no sizes. | Name the dimensions (channel, tier), n per group, and the minimum n required. (code: `subgroup_gate()`) |
| 9 | §28 | ECE 3.135% on 80 tickets gives no bin count. | Add n, bins and a small-sample caveat. (code: `ece()`) |

## Medium priority

- **§6 vs §28:** the metrics are duplicated word for word. Keep them in §28 only, and note that historical V1 (§9) and the frozen candidate share the classifier, so identical urgency figures are expected.
- **§21:** must-mention denominators (118 mentions across 59 tickets) show that only 59 of 200 references had requirements. Say so.
- **§23:** check the arithmetic (84/118 = 71.2%, 34/59 = 57.6%) and write the raw counts next to the percentages.
- **§12:** name the exact Qwen3 embedding model and size, and the hardware used for latency.
- **§16:** explain why `sufficient=None` rather than `False`: "not established" differs from "insufficient".
- **§20:** say explicitly that approval is recorded but never sends a message. (code: `/review` returns `customer_message_sent: false`)
- **§8, §26:** give the CI run for the final freeze, not only the V1 freeze.
- **§29:** add "routing precision on AUTO" to the not-measured list, since there were 0 AUTOs.

## Formatting

- The title is duplicated at the top, and a stray "Page" appears at the end.
- §35, §36 and §38 repeat the status. Merge them into one "Final status" section.
- Add author, date, report version and a one-table metrics summary on page 1.
- Use tables for metrics instead of one-line paragraphs, and add the pipeline diagram.
- Keep the three evidence populations (dev human-50, dev auto-200, validation-80) in a single table with columns for what each one measures.
