# Generate with independent review and repair

Read the generation and review references, [hosts.md](hosts.md) for isolation and [roles/repair.md](roles/repair.md) when correcting findings.

Collect with `collect --intent generate-review`. The coordinator AI chooses when to ask the user, invoke generation tools, start reviewers, repair and deliver. Python does not control that sequence or assemble agent prompts.

1. Author metadata using the generation guidance. Use `record-metadata` to check and accept the candidate; use `check --candidate` for read-only investigation when needed.
2. Export a current packet with `review-input --out RUN`, then start a fresh independent Reviewer with that packet and its frozen snapshots. Provide the role instructions and current review targets, excluding generation rationale and other reviewers' answers. Wait for its real candidate.
3. Call `record-review --candidate FILE --independent`. This flag attests actual host isolation; it cannot create or prove it.
4. Examine conflicts, meaningful unknowns and suggested-copy checks. Fix supported problems using `apply-patch`, or author a broader corrected candidate using `record-metadata`. The host may delegate Repair, but nested delegation is not required. Check again and obtain another fresh independent review after every accepted change or new evidence.
5. Deliver when metadata passes checks, the current independent review has no conflicts and remaining uncertainty is acceptable for the user's intended use. Summarize material unknowns and limitations without enumerating empty fields.

Default accepted/rejected-submission budget is eight; reduce it for a short task or use the user's smaller limit. Also stop on repeated versions, no progress, inadequate evidence, unavailable isolation or exhausted host resources. Use `stop --summary FILE` to explain an unfinished task. No tool automatically advances roles, retries indefinitely or exports incomplete work as successful metadata.

Successful outputs: `metadata.json`, `review.md`, `summary.md`. Upload requires its separately authorized action.
