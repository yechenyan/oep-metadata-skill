# Review existing metadata

Use this guide, [roles/reviewer.md](roles/reviewer.md) and the [tool contracts](evidence-and-outputs.md). Read them together with the source material when useful.

```bash
uv run --locked --project "$SKILL/scripts" python "$SKILL/scripts/oep_metadata.py" collect \
  --intent review --metadata input/metadata.json --data input/data.csv \
  --background input/source.md --out runs/review-01
```

Collection already returns the current reviewer view: metadata, original evidence, program checks and `context.review_fields`. Reuse it instead of an immediate unchanged inspection. The profile is present once; an evidence `content_ref` points to the same response's profile. Review targets omit example values, while preserving the schema meaning and exact pointers. Program-verified name/version entries are added separately.

Investigate meaningful uncertainties and ask for decisive missing evidence. Blank optional properties do not automatically become questions. Provide one opinion per review target. A short, specific reason is sufficient for a supported claim; conflicts and meaningful unknowns need enough explanation to assess the evidence. Avoid repeating a full paragraph for every supported field.

Call `record-review` and inspect the suggested-copy checks. Revise mechanically invalid suggestions before delivery. Original metadata is preserved in review-only work; reporting program errors in an invalid original is a valid outcome. The AI writes grouped user actions and calls `deliver` explicitly.

Human outputs: `review.md`, `summary.md`, and `metadata.suggested.json` only when corrections exist and the resulting copy passes checks. The report identifies the canonical target hash, separates agent judgments from automatic checks and shows conflicts/unknowns first. Its counts describe that target, not a later suggested copy. A new review of the suggested copy requires a new run.

## Fresh independent handoff

For a combined task the coordinator calls:

```bash
uv run --locked --project "$SKILL/scripts" python "$SKILL/scripts/oep_metadata.py" review-input --out runs/checked-01
```

This exports `RUN/.work/reviewer-input.json` with current metadata/evidence hashes, targets, checks, source snapshots, role instructions and a packet hash. It excludes generation provenance, prior opinions and previous candidates. Give the fresh Reviewer only that packet and its referenced frozen input snapshots, plus a permitted candidate output path. Resolve snapshot paths from the run directory. The host creates the fresh context and waits for its actual answer; the tool does not launch agents or advance roles. Read [hosts.md](hosts.md) for host isolation details.

An accepted change or supplementary evidence invalidates the old review and packet binding. Export a new packet and obtain a fresh review. `--independent` records the host's attestation; it cannot prove isolation.

## Review candidate contract

```json
{
  "input_hash":"CURRENT_INPUT_HASH",
  "metadata_hash":"CURRENT_METADATA_HASH",
  "summary":"Short assessment of this target.",
  "entries":[
    {"pointer":"/resources/0/title","decision":"conflict","comment":"The source states a different title.","evidence_ids":["REGISTERED_DOCUMENT_ID"],"proposed_value":"Documented title"}
  ]
}
```

Cover every context.review_fields pointer exactly once. Supported/conflict opinions require evidence; only conflicts can propose a replacement, also with evidence. Recording returns total decision_counts plus separate agent_decision_counts and program_decision_counts. The program labels origins itself; automatic checks do not inflate the number of agent judgments. No field opinion should merely repeat a generic approval without checking its evidence.

A reviewer-input packet already includes a hash-filled candidate_template, entry_contract, these role instructions and original evidence. A fresh Reviewer can work from it and its frozen snapshots without reading generation guidance or previous answers. Its packet_hash hashes the packet excluding that one key. metadata_hash always hashes canonical JSON, not raw file bytes. Accepted changes require a newly exported packet.
