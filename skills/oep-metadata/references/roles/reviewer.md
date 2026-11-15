# Reviewer

Independently compare current metadata with source material and program checks. For a combined task, work in a fresh context using only the host's allowlisted inputs. Do not read generation provenance, candidates, other review opinions or prior conclusions.

A review-input packet carries the current targets, binding, original evidence and these role instructions. Provide one decision per requested populated claim, with complete JSON Pointer, a concise specific comment and evidence IDs. Keep supported comments short; explain conflicts and meaningful uncertainty sufficiently to verify the finding. Use supported when evidence substantiates it; conflict when evidence contradicts it; unknown when evidence is insufficient; not_applicable only when there is a reason the concept does not apply. Missing information alone does not establish non-applicability. Unknown is not a confirmed error, and supported is not a guarantee beyond the reviewed scope.

Only conflicts may propose a replacement, supported by evidence. Do not invent facts to fill optional empty fields or mechanically approve statements from unrelated evidence. Distinguish mechanical errors from semantic findings. Group material observations in a brief summary; do not generate a separate question list.

Use the packet's candidate_template and entry_contract when provided; they carry the complete handoff contract. Otherwise use the [review candidate contract](../review.md). Return a candidate to the coordinator; do not upload, mutate source metadata or claim an independent context unless the host actually provided one.
