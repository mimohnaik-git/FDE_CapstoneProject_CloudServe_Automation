# Post-Freeze Stabilization Report

**Phase:** 5 — final engineering QA and stabilized-baseline preparation

**Evidence date:** 15 September 2026

**Frozen HEAD baseline:** `6a80e91a3b7a82504f04afa98cdb8265f7617234`

**Frozen V1 aggregate fingerprint:** `ddf89e82e7340a0257ee0c2ae1ce340612070545bc04f559e1e4c3ad733f59c1`

## Scope and evidence boundaries

This pass verifies the post-freeze engineering changes from Phases 2–4 and prepares a proposed commit boundary. It does not rerun evaluation, tune frozen behaviour, update submission reports, or create a commit.

- Validation dataset content was not opened, copied, fingerprinted, or executed.
- Hidden assessment data was not accessed or sought.
- The classification threshold remains `0.80`.
- The retrieval-routing threshold remains `0.30`.
- Classifier, retriever, routing policy, generation prompt, guardrails, evaluation metrics, and frozen V1 architecture were not changed in this phase.
- `evaluation/results/` is byte-unchanged relative to HEAD (`git diff --quiet -- evaluation/results` returned 0).

## Provider-artifact status investigation

Git reports the two tracked historical smoke results as modified:

- `artifacts/live_provider_generation_smoke/groq-result.json`
- `artifacts/live_provider_generation_smoke/openrouter-result.json`

This is an index/worktree line-ending metadata anomaly, not a content change. System Git configuration sets `core.autocrlf=true`; `git ls-files --eol` reports `i/lf w/mixed` for both files. For each file, `git hash-object <path>` exactly equals `git rev-parse HEAD:<path>`:

| File | Worktree and HEAD blob hash |
|---|---|
| Groq result | `0148fca8e7dcbd4c512c97243efe4e7963883978` |
| OpenRouter result | `0744f4968352edeadbd25a675adfe8a78cd348da` |

`git diff --numstat` and `git diff --raw` show no payload diff. The files were not rewritten, normalized, staged, or proposed for commit. Their false `M` status remains an explicit repository-state blocker until it can be cleared without touching historical evidence.

## Report-tooling source policy

The formatted DOCX is a required input to `scripts/build_formatted_report_docx.py`; it is therefore an intentional source asset, not disposable scratch state. It was moved without regeneration from:

`tmp/docx_template/MimohNaik_Capstone_Report_Formatted.docx`

to:

`assets/report_templates/MimohNaik_Capstone_Report_Formatted.docx`

The builder now resolves the asset repository-relatively. Its SHA-256 is `D3F2AF1E6AB9A72594E4820EEAA8B4DCAC4795708F8037ACF38AF983ED707039` (recorded from the moved file; the move did not alter content). Both report scripts use repository-relative inputs/outputs. No report, workbook, DOCX, or PDF was regenerated in this phase.

## Verification results

### Deterministic suite

All runs used Python 3.12.14, pytest 9.1.1, and `-W error`.

| Parent environment | Result | Warning result |
|---|---:|---:|
| `GENERATION_PROVIDER=offline` | 355 passed in 59.66s | 0 |
| `GENERATION_PROVIDER=openrouter` | 355 passed in 46.38s | 0 |
| `GENERATION_PROVIDER=groq` | 355 passed in 27.64s | 0 |

The root `tests/conftest.py` establishes offline mode before test-module imports and resets both the environment and cached settings for every ordinary test. Explicitly injected provider tests remain independent of this default. No real HTTP call occurred during any full-suite run.

### Focused provider and reliability tests

`tests/test_config.py`, `tests/test_generate.py`, `tests/test_reliability.py`, and `tests/test_provider_smoke.py`: **107 passed in 12.95s**, with warnings treated as errors.

Coverage includes provider selection, model resolution, missing credentials, timeouts, rate limiting, provider outages, malformed responses, structured-output validity, sanitized errors, offline behaviour, OpenRouter, and Groq.

### Clean-source reproduction

An allowlisted source export was created outside the repository and run with a parent OpenRouter environment. It contained no `.env` and excluded generated deliverables and the real validation dataset. A zero-byte validation-path placeholder was supplied solely for readiness tests that check path existence while monkeypatching loaders and fingerprinting to fail if invoked.

- Collected: 355 tests
- Result: **355 passed in 26.51s**
- `.env` present: no
- Validation placeholder size: 0 bytes
- Validation content read: no

This establishes source-tree portability and independence from developer-local provider configuration. The test reused the already stabilized project virtual environment; it was not a fresh dependency installation. Dependency reproducibility is supported by the Phase 3 isolated-environment evidence, the committed-style constraints file prepared in this worktree, the current successful requirements dry run, and `pip check`.

### Live-provider smoke status

Phase 4 preserved successful, synthetic, development-only live-smoke evidence for both OpenRouter and Groq: each provider returned HTTP 200, valid structured output, exact retrieved citations, and a safe guardrail rejection caused by the deliberately low-confidence synthetic classification.

In Phase 5, the single sandboxed OpenRouter attempt failed closed with `NETWORK_UNAVAILABLE`; no provider response payload was returned. A request to permit the external call was denied because it would transmit retrieved project documentation to an external provider without separately confirmed disclosure authorization. No bypass was attempted. The Groq call was not attempted for the same reason. Consequently, Phase 5 did not independently reproduce either live integration success; the preserved Phase 4 evidence remains the latest successful evidence.

The failed Phase 5 smoke output was written only under `tmp/phase5_live_smoke/` and is not proposed for commit.

## Static, dependency, and security checks

- `python -m compileall -q src tests evaluation scripts`: passed.
- Tracked JSON parse: 32 files passed; `data/raw/validation_tickets.json` was explicitly excluded.
- YAML parse: 2 files passed.
- `python -m pip install --dry-run -r requirements.txt`: requirements resolved from the active environment.
- `python -m pip check`: no broken requirements.
- `git diff --check`: passed; Git emitted only `core.autocrlf` conversion notices.
- `.env` tracked: no.
- Intended engineering files: zero detected OpenRouter secret patterns, Groq secret patterns, bearer-token patterns, or `C:\Users\...` absolute paths.
- Secrets printed or persisted by this phase: no.

## A1–A12 engineering confirmation

| Criterion | Phase 5 evidence | Status |
|---|---|---|
| A1 Clean checkout | External clean-source export, no `.env`, 355 passing tests | Confirmed for source execution; fresh dependency install not repeated |
| A2 Four channels | Ingestion regression tests passed | Confirmed |
| A3 Classification | Classification regression tests passed | Confirmed |
| A4 Retrieval | Retrieval and no-result regression tests passed | Confirmed |
| A5 Routing | Deterministic routing tests passed; thresholds unchanged | Confirmed |
| A6 Citation accuracy | Generation, grounding, and exact-citation tests passed | Confirmed at test level |
| A7 Guardrail blocking | Guardrail and reliability tests passed | Confirmed |
| A8 Decision logging | Logging and end-to-end audit tests passed | Confirmed |
| A9 Unattended evaluation | Harness tests passed; evaluation was not executed | Implementation confirmed only |
| A10 Automatic metrics | Metrics/framework tests passed; metrics were not regenerated | Implementation confirmed only |
| A11 Failure handling | Focused provider/reliability suite passed | Confirmed |
| A12 Tests | 355 passed in all three parent-provider environments | Confirmed |

This table is an engineering verification, not a claim that unmeasured business, human-evaluation, availability, or hidden-assessment targets were achieved.

## Exact Phase 5 file changes

- `scripts/build_formatted_report_docx.py` — changed the required template path from disposable `tmp/` storage to an intentional repository asset.
- `assets/report_templates/MimohNaik_Capstone_Report_Formatted.docx` — moved the existing template without regeneration so the report builder has a reproducible source input.
- `docs/post_freeze_stabilization_report.md` — added this authorized evidence report.

No production code changed in Phase 5.

## Proposed stabilized engineering commit

The following is the proposed commit allowlist; it has not been staged or committed:

- `.env.example`
- `.gitignore`
- `constraints.txt`
- `requirements.txt`
- `src/config.py`
- `src/generate.py`
- `scripts/live_provider_generation_smoke.py`
- `scripts/build_formatted_report_docx.py`
- `scripts/render_capstone_report.py`
- `assets/report_templates/MimohNaik_Capstone_Report_Formatted.docx`
- `tests/conftest.py`
- `tests/test_config.py`
- `tests/test_generate.py`
- `tests/test_pipeline.py`
- `tests/test_provider_smoke.py`
- `docs/post_freeze_stabilization_report.md`

Explicitly excluded are pre-existing report/document edits, generated PDFs/DOCX/workbooks, `audit_work/`, `output/`, `submission/`, development candidate/result artifacts not needed by runtime, all `tmp/` content, and the two false-modified historical provider JSON files.

## Remaining blockers

1. The two content-identical historical provider JSON files still display false `M` status because of Git line-ending metadata. They must not be included in a commit unless the anomaly is resolved without rewriting historical bytes.
2. Phase 5 live OpenRouter/Groq reproduction is not complete. External disclosure/network authorization is required to transmit the synthetic fixture's retrieved documentation to each provider. The application failed closed when network access was unavailable.
3. The worktree contains substantial pre-existing documentation and generated-deliverable changes outside the proposed engineering commit. Any eventual commit must use the explicit allowlist above and be reviewed before staging.

## Stop condition

Phase 5 stops here. No validation run, hidden-data access, report regeneration, Phase 6 work, staging, commit, or push was performed.

## Subsequent baseline confirmation

After this Phase 5 record was completed, the owner approved the audited allowlist as
a new post-freeze commit. Commit
`7062f683e41a178e644713acee81478731dc9adc` was created without amending frozen
commit `6a80e91a3b7a82504f04afa98cdb8265f7617234`. GitHub Actions run
`34889316386` completed successfully for the stabilized commit. This subsequent
confirmation does not change the Phase 5 execution record above, rerun validation,
or alter frozen evaluation evidence.
