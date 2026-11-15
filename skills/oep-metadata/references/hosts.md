# Host integration

The Skill uses portable instructions and Python tools. Local AI work runs in the host session; the CLI has no model SDK, prompt assembler, agent launcher or automatic role transitions.

## Invocation

From this repository root:

```bash
npx skills add ./skills/oep-metadata --skill oep-metadata -a codex --copy
```

For Claude Code use `-a claude-code`; include both host arguments to install for both. Project installation is the default; user-wide installation is an explicit choice. The canonical source is `skills/oep-metadata/`; installing copies only the Skill and its resources, not repository tests, docs or examples. Runtime dependencies need uv and the pinned Python 3.12 lock environment. First use may download packages.

Codex prompt: `Use $oep-metadata to generate metadata from input/data.csv using input/source.md.` Claude Code prompt: `/oep-metadata generate metadata from input/data.csv using input/source.md`. For an uninstalled source checkout, explicitly reference its SKILL.md.

Resolve `SKILL` from the loaded instruction file at runtime. Use project-relative inputs and a new run directory. The host AI writes commands, candidates and summaries; the human supplies intent, files and needed facts. A human does not have to manually implement a CLI protocol.

## Independent review

For combined work, start each Reviewer in a new context. In Codex use a noninheriting agent, such as `fork_turns="none"` when available. In Claude Code use its fresh non-fork agent capability. Inspect actual tool availability; do not change user settings to bypass depth/tool restrictions. Repair can run in the coordinator or a delegated child; a fixed nested agent topology is not required.

Allowlist Reviewer inputs: role/reference instructions, current metadata, profile, database constraints, review targets/specifications, original evidence snapshots and current program checks. Use `review-input --out RUN` to export these inputs without generation provenance or prior opinions. The host builds the isolated task from that packet. `inspect --view full` includes provenance and possibly prior review: extract an isolated reviewer input, do not hand over that entire response. Exclude generator rationale, generation candidates, earlier reviewers' answers, parent history and evaluation oracles. Shared filesystem access is not a security sandbox; enforce the read boundary in host instructions.

Wait for the actual candidate, then record it. `--independent` records the host's attestation, not measured isolation or model identity. If a fresh context is unavailable, explain it and stop the combined task; offer plain generation only as an explicit scope change.

## Resume and portability

Use `inspect --out RUN` to continue an open tool run. Hashes and snapshot checks detect stale candidates and changed inputs. Copy the complete run for relocation; use plan filenames for resuming uploads so their directories bind at runtime. Never persist personal machine paths. Closed runs and older state-machine runs require a new run directory.

Program tests are host independent. Codex independent-agent behavior has been exercised; actual Claude Code end-to-end execution and production remote writes remain outside the verified boundary.
