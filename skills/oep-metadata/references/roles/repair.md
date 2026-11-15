# Repair

Read current metadata, evidence, checks and current review findings. Correct evidence-backed conflicts and material uncertainties; avoid rewriting unrelated fields. Ask for decisive missing information instead of inventing values.

For targeted changes, return the apply-patch contract: current input_hash/base_hash, replace operations, matching old values, evidence and reasons. The tool checks the whole result. For changes requiring a full candidate, use record-metadata and the provenance contract in generate.md. Source structure remains protected.

The host AI interprets failed checks and revises. An accepted change invalidates the previous review; request a fresh independent Reviewer before combined delivery. Stop when evidence or progress is insufficient. Do not replace uncertainty with an unsupported claim to silence a finding.

Patch candidate example:

```json
{
  "input_hash":"CURRENT_INPUT_HASH",
  "base_hash":"CURRENT_METADATA_HASH",
  "patches":[
    {"op":"replace","pointer":"/resources/0/title","old_value":"Old title","value":"Documented title","evidence_ids":["REGISTERED_DOCUMENT_ID"],"reason":"Match the source."}
  ]
}
```

Use nonempty, nonoverlapping replace operations within current conflict/unknown pointers or their descendants. Match the actual old value. The full result must pass checks and provenance/structure guards. The tool does not decide whether a correction is semantically warranted.
