# Upload metadata or field opinions

Local work does not authorize remote writes. Use the user's already-authorized target/action when provided. If missing, finish the local artifact and concrete plan first, then obtain only the missing decision. Do not repeat confirmation for the same clearly authorized action.

## metadata-upload

Only update metadata of an existing OEP table; creating tables, uploading rows and publishing tables are separate.

Prepare a plan:

```bash
uv run --locked --project "$SKILL/scripts" python "$SKILL/scripts/oep_metadata.py" metadata-upload \
  --metadata examples/selected-metadata.json --table TABLE --out examples/upload-plan
```

Plans are saved as `upload.plan.json` inside the selected output directory. Read the plan/validation/diff, confirm the exact target and inspect evidence gaps. Pass that plan filename and the same output directory when executing; directory checks resolve from the plan file, independently of the current working directory:

```bash
uv run --locked --project "$SKILL/scripts" python "$SKILL/scripts/oep_metadata.py" metadata-upload \
  --metadata examples/selected-metadata.json --table TABLE --out examples/upload-plan \
  --execute --plan examples/upload-plan/upload.plan.json
```

Credentials are read from `OEP_API_TOKEN`; populate through an approved secret mechanism, never a candidate, prompt, plan or report. Bind the file hash and target origin/schema/table; preserve current remote metadata and re-read before execution. Refuse stale plans. Client pre-read is not atomic concurrency control.

Metadata upload requires a confirmed inactive Open Peer Review state both when preparing the plan and immediately before execution. A timeout, failed read or unfamiliar page layout leaves this state unverified and blocks execution. Retain the plan/backup/diff, resolve the check and prepare a new plan; an older plan marked executable cannot override an unverified status.

Read back after upload and save a receipt with target, hashes, timestamps and verified outcome. An uncertain write response requires read-back before any retry. Keep tokens out of artifacts/logs.

## review-upload

This saves/submits field opinions in OEP Open Peer Review; it is not a generic comment, metadata replacement or automatic platform certification of a local AI review.

```bash
uv run --locked --project "$SKILL/scripts" python "$SKILL/scripts/oep_metadata.py" review-upload \
  --metadata examples/reviewed-snapshot.json --review examples/final-review.json \
  --table TABLE --action save --review-id REVIEW_ID --out examples/review-plan \
  --cookies examples/session-cookies.txt
```

Use `--action submit` only for the user's authorized submit action. For a new review, first use `--action save` without `--review-id`; verified execution discovers the ID. Prepare a separate submit plan with that ID and a new output directory. Do not guess an ID. The Netscape session-cookie jar stays outside artifacts. API Token and web session credentials are not interchangeable.

After inspecting the mapping and plan, invoke the same command with `--execute --plan ACTUAL_PLAN_PATH`. Do not use `finished`, grant badges, or impersonate another account. Contributor/reviewer separation remains in force; a subagent is not another platform identity.

Repeat the original table, action, review ID (when present) and output directory when executing. Optional `--plan-hash` binds the displayed plan hash. Unknown opinions block submit; save may retain an incomplete working draft. Multi-resource documents, empty-field additions and typed/structural edits that the current OPR form cannot express are rejected. All-accepted review requires finish/badge handling outside this first version.

Verify current role, review snapshot, field IDs, action and round. Report opinions the platform cannot express. Unknown/not-applicable do not automatically map to Accept. Do not silently omit unresolved required opinions. If metadata changed, do not apply stale opinions to its replacement.

The adapter targets source-backed authenticated web/CSRF behavior; source inspection and local fixtures do not prove compatibility with production. If authentication/protocol/role is unavailable, retain the local plan/report and state the concrete limitation. Do not weaken authentication or modify OEP source.

Read back and record status/URL/receipt. A plan or HTTP success alone is not proof the platform saved the opinions. Do not blindly repeat ambiguous submit. Report whether a real remote write occurred and whether deployment compatibility was verified.
