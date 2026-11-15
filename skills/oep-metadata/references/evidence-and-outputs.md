# Shared tool contracts

The host AI selects actions and interprets results. Tools do not schedule roles, call a model or automatically deliver. Use the CLI prefix from SKILL.md; resolve SKILL from the loaded instruction file.

## Results and views

Results are compact JSON on stdout. Put `--pretty` before the tool name for indented diagnostics. Exit 0 means success, 1 means a failed check/gate, and 2 means a bad request, stale input or operational error. Caught errors are JSON on stderr; argument-parser usage errors use text.

`collect` already returns the current task input; reuse it. `inspect --out RUN` refreshes it when needed. CLI views are generation for generate/generate-review, reviewer for review. `--view full` exposes complete internals for debugging, including provenance and possibly old opinions; keep it outside independent Reviewer inputs. `--view status` on inspect returns status/checks without full metadata. Python API callers retain the full view by default.

Task views preserve original text, metadata, hashes, evidence and snapshots. A profile is returned once. An evidence `content_ref` such as `/context/profile` is a JSON Pointer into that same response, not another file. Snapshot paths resolve from RUN; `schema_from_skill` resolves from the loaded SKILL.md directory. The full internal snapshot is `RUN/.work/context.json`.

## Tools

| Tool | Arguments and purpose |
| --- | --- |
| `collect` | `--intent generate\|review\|generate-review --out RUN`; freeze sources and return current input. |
| `inspect` | `--out RUN [--view generation\|reviewer\|status\|full]`; read current state. |
| `record-metadata` | `--out RUN --candidate FILE`; validate and accept one metadata envelope. |
| `check` / `validate` | `--candidate FILE` or `--metadata FILE`, optionally `--run RUN`; read-only mechanical check. |
| `record-review` | `--out RUN --candidate FILE [--independent]`; record current field opinions. |
| `review-input` | `--out RUN`; export `.work/reviewer-input.json` without generation reasoning or old opinions. |
| `apply-patch` | `--out RUN --candidate FILE`; validate an evidence-backed correction. |
| `evidence-add` | `--out RUN --file FILE --kind declaration`; freeze supplementary text and invalidate old bindings. |
| `deliver` / `stop` | `--out RUN --summary FILE`; export an explicitly chosen outcome. |
| `schema` | `--pointer /resources/0/temporal`; return only that field specification, not the full schema. |
| `profile` / `template` | `--data FILE` / `--profile FILE`; inspect data or make a neutral template independently. |

Generation takes one `--data FILE` or `--table TABLE`, excluding existing metadata. Review takes `--metadata FILE` or an OEP table, with optional data. Repeated `--background FILE` attaches multiple UTF-8 documents. Local data: CSV/TSV or JSON row arrays; extract PDF/Office text first. Links are not crawled automatically. Remote sampling coverage is reported.

Collection options: `--max-rows N`, `--ontology-index FILE`, `--base-url URL`, `--max-changes N` (default 8, range 1-30). The budget counts accepted changes and mechanically rejected submissions. Also stop when host resources, evidence or progress are exhausted.

`profile` returns `{ok, profile}`. Both that envelope and a bare profile work with `template --profile` and `check --profile`; malformed inputs fail explicitly. `check` recognizes metadata candidate envelopes, so a second bare copy is unnecessary. It checks metadata; recording additionally enforces provenance, hashes and structure. Standalone check can use `--profile FILE --db-schema FILE --ontology-index FILE` instead of `--run`.

Ontology helpers: `ontology-index --source FILE --version VERSION --out FILE`, `ontology-search --index FILE --query TEXT`. Frozen-index existence does not establish semantic suitability.

## Evidence and bindings

Use current `input_hash`, `metadata_hash`, exact JSON Pointers and registered evidence IDs. The input hash binds the full internal context, not the reduced response view. Collection-supplied original filenames may differ from normalized snapshot names; a filename is not proof of identity or remote provenance.

Changed populated leaves require supported evidence. Licenses, identities/authors and non-null declarations need documentary/declaration evidence, not a value profile. No observed nulls does not establish NOT NULL. Preserve unknowns; schema validity and evidence references do not prove factual correctness. See the selected workflow for its candidate shape: [generation](generate.md), [review](review.md), [repair](roles/repair.md).

An accepted metadata change or new evidence changes input bindings and invalidates the review. Recording opinions does not change the input hash. Repeated versions are refused; the AI chooses whether to stop or investigate. Source field names/order/resource count and declared database types remain protected; profile-inferred types can be revised with evidence.

## Summary and delivery

The AI authors a summary input:

```json
{"overview":"Short outcome","needs_attention":["Grouped user action"],"notes":["Dataset-specific limitation"]}
```

Each list allows at most eight concise items, not one per null field. The tool adds validation status, warning count and review boundary; authored notes should not repeat those automatic statements.

| Intent | Human outputs |
| --- | --- |
| Generate | `metadata.json`, `summary.md` |
| Review | `review.md`, `summary.md`; `metadata.suggested.json` only for corrections that pass checks |
| Combined | `metadata.json`, `review.md`, `summary.md` |
| Stopped | `summary.md` only; no successful metadata delivery |

Combined delivery requires valid accepted metadata and a current independent review with zero conflicts. Unknown judgments may remain if explained. Empty optional facts are not automatically review targets or questions. A review report remains bound to its original target; a suggested copy needs a separate run to receive a new review.

## Internal records

Use a new empty RUN. Put AI exchanges under `.work/authoring/`; reserve root files for deliverables. `.work/` holds frozen sources, context, accepted revisions and machine-readable opinions. Review upload uses `.work/review.json` and its matching snapshot; human users normally read Markdown.

CLI calls append timing/exit/response-size/binding diagnostics to `.work/tool-events.jsonl`; reads may append diagnostics without changing metadata/state. They exclude host/model latency and Python startup. No `questions.json` or `validation.json` is created. Program checks are tool responses and are embedded in review.md when applicable.

Copy the complete RUN for relocation. Open runs resume through inspect; closed runs require a new task directory. Derived packet exports and diagnostics may be produced from closed runs. Do not manually edit hash-bound files. Older state-machine runs are historical and require a new directory.
