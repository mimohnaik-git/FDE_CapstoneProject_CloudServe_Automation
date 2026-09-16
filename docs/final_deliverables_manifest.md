# Final Deliverables Manifest

Administrative reconciliation date: 15 September 2026. This is an inventory, not a
claim that the final submission archive has been assembled. Engineering stabilization
is complete at commit `7062f683e41a178e644713acee81478731dc9adc`, with successful
GitHub Actions run `34889316386`. Documentation reconciliation is in progress. The
existing `submission/` tree is a pre-reconciliation staging reference whose source
snapshot predates the stabilized baseline; it is not submission-ready.

Status terms: **READY** means evidence content exists; **PARTIAL** means content exists
but is stale, incomplete, or in the wrong format; **MISSING** means the required final
artifact does not exist; **OWNER ACTION** means the project owner must supply or approve
the final judgement/output.

## Required archive contract

The final archive must be named `FirstnameLastname_Capstone_Submission.zip`, with the
project owner's exact enrolment name, no spaces, dates, or version suffixes. It must not
contain a wrapper directory and must have exactly:

```text
01_Video/
02_Report/
03_Workbooks/
04_Source_Code/
```

Current status: **PARTIAL**. Pre-reconciliation `03_Workbooks/` and `04_Source_Code/`
staging content exists under `submission/`, but both require refresh after documentation
reconciliation. `01_Video/`, `02_Report/`, the final visual/text QA, and the compliant
enrolment-name archive are not complete.

## Content audit

| Deliverable | Current evidence/input | Required final destination | Status | Audit finding/action |
|---|---|---|---|---|
| Discovery artifacts | `docs/stage_1_discovery_workbook.md`; stakeholder and dataset source files in `capstone_pack/05_Datasets/` | Workbook/report appendices | READY | Owner review is complete; reconcile remaining workbook-template gaps before export. |
| PRD v1 | `docs/stage_2_prd_template.md` | Report/workbook evidence | PARTIAL | Product requirements remain historical; implementation status now distinguishes FR-04 PARTIAL from A5 PASS. Regeneration is pending. |
| Prompt/specification artifacts | `docs/stage_3_prompt_library.md`; `prompts/`; Build Specification in `capstone_pack/01_Read_First/` | Report appendices and `04_Source_Code/` | READY | Preserve versions; verify the report distinguishes reference prompts from frozen production prompt. |
| Requirements traceability | `docs/requirements_traceability.md` | `04_Source_Code/docs/` and report appendix | READY | Current implementation statuses and operational NOT MEASURED boundary are recorded. |
| Architecture documentation | `docs/architecture.md`; `docs/architecture_decisions.md`; `docs/technical_defense_qa.md` | `04_Source_Code/docs/` and report | READY | Current MiniLM/NumPy/direct-Python design is documented. |
| Evaluation evidence | Stage 9–16 JSON/Markdown and freeze manifests under `evaluation/results/` | `04_Source_Code/evaluation/` and report appendix | READY | Preserve Stage 13 and Stage 16 artifacts and disclose the rerun. Decision SQLite files are ignored runtime evidence and require an explicit packaging decision. |
| Fairness evidence | `evaluation/results/stage18-fairness.json` and `.md` | `04_Source_Code/evaluation/` and report | READY | Underpowered groups remain NOT MEASURED. |
| Human-review evidence | `evaluation/results/stage18-human-evaluation.json` and `.md`; sample/reviewer files under `human-development-evaluation/` | `04_Source_Code/evaluation/` and report | READY | State 2% hallucination and 98% semantic citation accuracy as HUMAN DEVELOPMENT EVALUATION only. Preserve raw completed reviews. |
| Governance | `docs/governance.md`; monitoring configuration; kill-switch implementation/tests | `04_Source_Code/` and report | READY | Operational performance remains NOT MEASURED. |
| PRD revision / PRD v2 | `docs/stage_5_prd_revision_log.md`; `docs/prd_v2.md` | Workbook/report requirements-revision section | PARTIAL | The revision log preserves frozen V1 and rejected V2 while recording post-freeze implementation hardening. No PRD V3 or product-requirement change was created. PDF regeneration is pending. |
| Workbook 1 | `docs/stage_1_discovery_workbook.md` | `submission/03_Workbooks/Stage_1_Discovery_Workbook.pdf` | PARTIAL | Discovery source remains current and unchanged; final-set regeneration and visual/text QA remain pending. |
| Workbook 2 | `docs/stage_2_prd_template.md` | `submission/03_Workbooks/Stage_2_PRD.pdf` | PARTIAL | Completed PDF is assembled; refresh it after the corrected latest-CI reference. |
| Workbook 3 | `docs/stage_3_prompt_library.md` | `submission/03_Workbooks/Stage_3_Prompt_Library.pdf` | PARTIAL | Frozen prompt source remains current and unchanged; final-set regeneration and visual/text QA remain pending. |
| Workbook 4 | `docs/stage_4_sprint_plan.md` | `submission/03_Workbooks/Stage_4_Sprint_Plan.pdf` | PARTIAL | Completed PDF is assembled; refresh it after the effort and latest-CI administrative updates. |
| Workbook 5 | `docs/stage_5_prd_revision_log.md` | `submission/03_Workbooks/Stage_5_PRD_Revision_Log.pdf` | PARTIAL | Completed PDF is assembled; refresh it after the corrected latest-CI reference. |
| Effort log | `docs/effort_log.md` | `submission/03_Workbooks/MimohNaik_Effort_Log.pdf` | PARTIAL | Owner-approved 51.5-hour reconstructed estimate is documented and exported; rename/refresh the submission copy after the corrected latest-CI reference. |
| AI-use declaration | `docs/ai_use_declaration.md` | Report and/or workbook evidence | READY | Confirmed tools, corrections/overrides, owner responsibility, name, and date are recorded. Include it in the report/package. |
| Final report input | `docs/final_capstone_report.md`; claim/evidence registers | `02_Report/FirstnameLastname_Capstone_Report.pdf` | PARTIAL | Post-freeze source reconciliation is in progress. The required single 20–30 page PDF must still be regenerated and inspected. |
| Video/demo input | `docs/video_presentation_script.md`; README/API/evidence artifacts | `01_Video/FirstnameLastname_Capstone_Video.mp4` or link text file | PARTIAL | Current evidence-aware script exists; no recording/link exists. Required 18–22 minute, 1080p video must include presenter visibility and >=7 minutes of live demonstration. |
| Complete source repository | Repository root, `.github/workflows/ci.yml`, README, source/tests/evaluation/docs/data | `submission/04_Source_Code/` | PARTIAL | Engineering stabilization is complete at commit `7062f683e41a178e644713acee81478731dc9adc`; GitHub Actions run `34889316386` succeeded with dependency installation, consistency checks, offline startup, and 355 tests. The existing source snapshot is stale and must be refreshed after reconciliation. CI is reproducibility evidence, not availability evidence. Repository-history delivery remains unresolved. |
| Final archive | None | `FirstnameLastname_Capstone_Submission.zip` | MISSING | Requires owner name and all final files above. Do not create until contents are final and reviewed. |

## Frozen evidence preservation baseline

These files were hashed during this audit and must not be overwritten:

| Artifact | SHA-256 |
|---|---|
| `validation-final.json` | `ae2e2037139e55b6ea0a8180ceb3b0299dce850e052505d69232a2328050758f` |
| `validation-final.md` | `ebafde60f216bacfdc0dc9da361a3fecfad8a68b8bf94299d835fac4da03ab07` |
| Stage 13 decision database | `262ddc6b4aa993971ed630b751fcea8b9cbe11f06c8925ec03fe7426478c049f` |
| `validation-technical-rerun.json` | `e4d2ac41588df8fadc985190c86da3412eb66ad9442ddb57b1f8772ddacd7725` |
| `validation-technical-rerun.md` | `0ff2a2000f0ca42f2771eda2995dcd41b490e2be3720e2c500c34569fda97691` |
| Stage 16 decision database | `fd5a7479c3d5db5dc99777c9bc9e071d64d087b3759a217f4f7d3d9362cb9d1f` |
| `stage18-human-evaluation.json` | `e42124b0eef095fc7d8c02361c5858abceaf4bcba1ae160bab4599469537fd45` |
| `stage18-human-evaluation.md` | `6602255e86983b86e7ff6b9b695e63ac64e3fe4825498f85a21a445f6983c8e5` |
| `stage20-v2-development.json` | `11e49ba834e7b8e6a9f5ad3eafbe21d3915db38167c4c3e7ac5ff6c044df86ae` |

## Packaging blockers

1. Final MP4 or video-link text file is missing.
2. Final 20–30 page PDF report is missing.
3. The existing seven report/workbook artifacts require controlled regeneration and
   final visual/text QA from the reconciled sources; the effort-log filename must use
   the owner name.
4. The final four-folder archive has not been assembled or inspected.
5. A deliberate decision is required on including ignored SQLite decision databases as
    frozen evaluation evidence without treating other runtime DBs as source artifacts.
6. The original pack requires repository history; the final delivery mechanism for that
   history has not been specified.

## Final audit procedure

After the owner resolves the blockers, run the packaging script, then inspect the ZIP
without executing evaluation. Confirm exactly four top-level folders, required filenames,
no wrapper directory, no cache/runtime/secrets, readable PDF/video, five completed
workbooks plus effort log, full repository contents, and preserved evidence hashes.
