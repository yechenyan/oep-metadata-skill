# Generate metadata

Use this guide, [roles/generator.md](roles/generator.md) and the [tool contracts](evidence-and-outputs.md). They can be read together with the supplied documents. Host-specific integration is needed for installation or independent review.

```bash
uv run --locked --project "$SKILL/scripts" python "$SKILL/scripts/oep_metadata.py" collect \
  --intent generate --data input/data.csv --background input/source.md --out runs/draft-01
```

`collect` already returns the current generation view: template, one profile, complete supplied text evidence, IDs, hashes and snapshot locations. Reuse that response. A second unchanged `inspect` adds no new input. Inspect again when needed after evidence or working metadata changes; use `--view full` for internal diagnostics.

Read the material before asking for decisive missing facts. Register substantive answers with `evidence-add --kind declaration` and use the refreshed hashes. Repeated `--background` arguments attach multiple documents.

Write one candidate envelope under `RUN/.work/authoring/` with `input_hash`, the full `metadata` and leaf-level `provenance`. Use ordinary JSON serialization; do not add a literal escaped newline after a JSON document. Source-observed names/order remain protected; value-inferred types can be corrected using evidence.

A minimally populated resource data-license object is:

```json
{"name": "CC0-1.0"}
```

Use this only if the source declares that SPDX identifier. Its `/resources/0/licenses/0/name` leaf needs supported documentary provenance. Data licensing does not select a metadata license. For one field's meaning use `schema --pointer /resources/0/licenses/0/name` rather than reading the entire schema. The complete schema is at `$SKILL/assets/oemetadata-2.0.4/schema.json`.

Year-only scenario coverage belongs in descriptions, for example "Scenario years 2035 and 2040". If the source supplies no exact date/time, leave referenceDate null and timeseries empty rather than inventing January 1 or year-end timestamps. `schema --pointer /resources/0/temporal/timeseries/0/start` shows the required date-time format; a schema format does not justify precision missing from the source.

Submit the envelope with `record-metadata --out RUN --candidate FILE`. This checks the whole metadata and enforces hashes/provenance before acceptance. If rejected, read the tool errors and revise; a mechanical rejection preserves the working metadata and current hash. For a separate read-only check use `check --candidate FILE --run RUN`. A bare document uses `check --metadata FILE`; candidate envelopes passed there are also recognized. There is no need to create a second full metadata copy solely for checking.

Acceptance stores a working revision. The AI decides whether to revise, ask or deliver. Author a short summary, then call `deliver --out RUN --summary FILE`; final validation is repeated. Outputs are `metadata.json` and `summary.md`. The tool adds check status and the review boundary; summary notes should focus on dataset-specific facts rather than repeat that boilerplate. If completion is impossible, use `stop` with an honest explanation.

## Candidate shape and local authoring

```json
{
  "input_hash": "CURRENT_INPUT_HASH",
  "metadata": {},
  "provenance": [
    {"pointer":"/resources/0/title","status":"supported","evidence_ids":["REGISTERED_DOCUMENT_ID"],"rationale":"Title stated in the source."}
  ]
}
```

Replace metadata with the full document. Each changed populated leaf requires supported provenance. Unknown provenance allows only empty/null or ToDo; not_applicable requires null and a reason. Avoid ToDo where it could look like a real fact. Retained unchanged claims need not be re-authored.

For a local authoring script, use the supported snapshot shape instead of copying the template from a terminal response. This example only loads and serializes the envelope; author evidence-backed metadata/provenance changes before submitting it:

```python
import copy
import json
from pathlib import Path

run = Path("runs/draft-01")
context = json.loads((run / ".work/context.json").read_text())
candidate = {"input_hash": context["input_hash"],
             "metadata": copy.deepcopy(context["metadata"]), "provenance": []}
# Fill candidate metadata and provenance from the actual supplied evidence.
path = run / ".work/authoring/metadata.candidate.json"
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("w", encoding="utf-8") as stream:
    json.dump(candidate, stream, ensure_ascii=False, indent=2)
```
