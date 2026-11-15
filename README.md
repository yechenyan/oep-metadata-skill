# OEP Metadata Skill

Generate, review and upload [Open Energy Platform](https://openenergyplatform.org/) metadata with an AI coding agent. **The AI drives the task**: it reads your material, asks necessary questions, writes metadata, uses Python tools to check it, corrects errors and decides when to deliver. The supported format is **OEMetadata 2.0.4**.

Open the step-by-step guide in [English](index.html), [Chinese](index-zh.html) or [German](index-de.html), including commands, AI inputs and candidate output examples. It works offline and illustrates the workflow; it does not execute it.

## 1. Getting started

You need an AI coding agent, [uv](https://docs.astral.sh/uv/), and Node.js/npm for installation. Local AI work uses your agent session without a separate model API key. Python dependencies are locked and resolved on first use.

### Install

From the project where you want to use the Skill, install it from GitHub for Claude Code:

```sh
npx skills add yechenyan/oep-metadata-skill --skill oep-metadata -a claude-code
```

For Codex replace `-a claude-code` with `-a codex`; include both to install for both. This installs only the Skill from `skills/oep-metadata/` into the current project without cloning the repository yourself. Add `-g` only for a user-wide installation.

### Try the smallest example

Keep the repository open in your agent and send:

> Use $oep-metadata to generate metadata from `examples/capacity.csv` using `examples/capacity-source.md`. Save to `runs/capacity-01`. Check the metadata and correct mechanical errors before delivery. Leave unsupported facts unknown and briefly explain anything I need to confirm. No independent review or upload.

For Claude Code replace `Use $oep-metadata` with `/oep-metadata`. The example contains four synthetic wind-capacity observations in MW. Its documentation intentionally leaves some publication details unspecified.

### Read two files

| File in `runs/capacity-01/` | What you use it for |
| --- | --- |
| `metadata.json` | The generated document, checked before delivery. |
| `summary.md` | A short outcome, grouped actions and material caveats. |

You do not need to read internal check responses or a separate question JSON. Missing facts stay unknown; passing checks does not make the document complete or prove its claims. Use a new output directory for another run.

## 2. Features

These are five user capabilities, selected through your prompt. The AI invokes individual tools as needed; a Python command does not run an AI workflow by itself.

| Capability | What happens | Human-facing outputs |
| --- | --- | --- |
| Generate | AI reads data/docs, writes metadata, checks and corrects it, then delivers. | `metadata.json`, `summary.md` |
| Review | AI compares existing metadata with evidence and checks, records findings and optional corrections. | `review.md`, `summary.md`; valid `metadata.suggested.json` when corrections exist |
| Generate with independent review | AI generates, starts a fresh Reviewer, corrects supported findings and obtains a new review after changes. | `metadata.json`, `review.md`, `summary.md` |
| Upload metadata | Validate, prepare backup/diff/plan, execute the authorized update and verify read-back. | Plan, backup/diff and execution receipt |
| Save or submit review | Map recorded opinions to OEP Open Peer Review, prepare a plan, save or submit the authorized action and verify. | Plan, mapping/backup and execution receipt |

### Generate metadata

> Use $oep-metadata to generate metadata for `input/data.csv`, using `input/methods.md` and `input/codebook.md`. Save to `runs/draft-01`. Ask only for facts that materially change the result, fix program errors and deliver a concise summary. No independent review or upload.

The AI interprets the material and cites evidence for its changes. You can attach multiple background documents. Program checks are tools for the AI; it handles fixable errors before handing you a result. Unsupported licenses, contacts and other facts are not guessed.

[Generation details](skills/oep-metadata/references/generate.md)

### Review existing metadata

> Use $oep-metadata to review `input/metadata.json` against `input/data.csv` and `input/source.md`. Save to `runs/review-01`. Show actual conflicts and meaningful uncertainties first, with a short summary of actions. Keep the original unchanged. No upload.

`review.md` contains grouped findings and program checks. `summary.md` groups what you should act on. A proposed metadata copy is separate and exported only if it passes checks; an invalid original can still receive a valid review report.

[Review details](skills/oep-metadata/references/review.md)

### Generate with independent review and repair

> Use $oep-metadata to generate metadata from `input/data.csv` and `input/source.md`, then have a fresh independent agent review it. Repair evidence-backed problems and obtain a fresh review after each change, with at most two repair rounds. Save to `runs/checked-01` and explain remaining limitations. No upload.

The AI coordinates the roles and uses checks during correction. Successful delivery requires mechanically valid metadata and a current independent review with no conflicts. Material unknowns are explained; if evidence, isolation or progress is insufficient, the AI stops and writes `summary.md` without claiming successful metadata delivery.

[Combined workflow details](skills/oep-metadata/references/generate-review.md)

### Upload metadata to OEP

> Use $oep-metadata to prepare an upload plan for `input/metadata.json` to existing table `your_table` at `https://openenergyplatform.org`. Save the plan, remote backup and diff to `runs/upload-01`. Show the proposed changes without executing them.

After inspecting the plan, an execution request can be:

> Execute `runs/upload-01/upload.plan.json` for `input/metadata.json`, table `your_table`, using `runs/upload-01` as the output directory. Read the token from `OEP_API_TOKEN`. Read back the metadata and report whether the update was verified.

This updates an existing table's metadata. Table creation, data-row upload and publication are separate. Execution checks the inactive Open Peer Review state and binds the payload, target and selected plan.

### Save or submit review opinions to OEP

> Use $oep-metadata to prepare a plan to save the recorded opinions from `runs/review-01` as a new Open Peer Review draft for table `your_table` at `https://openenergyplatform.org`. Use its matching reviewed snapshot and my authorized session-cookie file `secrets/oep-cookies.txt`. Save the plan to `runs/review-save-01` without executing it.

The AI reads `.work/review.json` and the matching `.work/original.metadata.json` internally. For a combined run, the reviewed snapshot is the delivered `metadata.json`. You normally read the Markdown report. The adapter checks account role and the platform's frozen snapshot, then maps supported opinions. Saving and submitting are different actions; submitting a saved draft requires a new plan using its verified review ID.

Both adapters prepare plans by default. Execution uses `--execute --plan FILE` and verifies the result. **Production writes remain unverified; upload tests use simulated HTTP responses.**

[Upload details](skills/oep-metadata/references/upload.md)

## 3. Evidence, results and limitations

### What to supply

- One dataset per generation run: UTF-8 CSV/TSV, a JSON array of rows or an OEP table. Remote sampling coverage is reported.
- Any number of background documents: methods, codebooks, README text or explicit declarations. Extract PDF/Office text first. Collection does not automatically crawl links.
- An optional frozen OEO index for identifier existence checks; the AI must still assess semantic suitability.

The AI reads supplied documents before asking you for material missing facts. It records substantive answers as evidence, revises metadata and checks again. Optional blank properties do not automatically become dozens of questions. No `questions.json` or `validation.json` is generated.

### Understanding the review

| Decision | Meaning | Typical action |
| --- | --- | --- |
| `conflict` | Evidence contradicts the value. | Inspect and correct. |
| `unknown` | Evidence is insufficient to judge the value. | Supply evidence or retain uncertainty; this is not a confirmed error. |
| `supported` | Evidence supports the value within scope. | Usually none; details are collapsed. |
| `not_applicable` | A reasoned judgment that the concept does not apply. | Usually none if justified; details are collapsed. |

These are categories, not severity scores. `review.md` counts each group, shows conflicts and unknowns first and includes program errors/warnings directly. It does not list every empty template field as an issue. The short summary groups user actions instead of repeating all field decisions.

### Checks and internal records

Successful generated metadata must pass schema, format and available data/constraint checks. The AI fixes mechanical failures in a bounded loop; missing essential evidence can prevent completion. Unknown values remain where the schema permits. Mechanical validity, citations and agreement between agents do not prove factual correctness.

`.work/` contains frozen evidence, hashes, accepted revision history and machine-readable review opinions for tools. It also holds lightweight CLI timing events. `review-input` exports a clean hash-bound packet for an independent Reviewer. CLI responses use compact JSON and task-specific views; `--pretty` and `inspect --view full` provide detailed diagnostics. These are internal records. Copy the complete run when relocating it, and ask the AI to inspect an open run to resume. Closed runs require a new directory. Previous state-machine runs remain historical; they cannot be resumed by the new tools.

Independent review depends on the host providing a fresh context; the flag records an attestation. Codex workflows have been exercised. Actual Claude Code end-to-end execution remains unverified.

[Tool contracts and outputs](skills/oep-metadata/references/evidence-and-outputs.md) · [Host integration](skills/oep-metadata/references/hosts.md)

## 4. Deployment and development

This Skill runs inside an AI coding agent. There is no server to deploy. Distribute the complete `skills/oep-metadata/` folder through `npx skills` or copy it into the host's Skill directory. Repository tests, examples and the guide stay outside the installed Skill.

`uv` resolves Python 3.12 and locked dependencies. First use needs network access or a populated cache. Upload credentials are separate: `OEP_API_TOKEN` for metadata updates and an explicitly supplied Netscape session-cookie file for Open Peer Review. Keep them outside artifacts and version control. Local generation/review needs neither credential.

### CLI tools

```sh
uv run --locked --project skills/oep-metadata/scripts \
  python skills/oep-metadata/scripts/oep_metadata.py --help
```

Tools include `collect`, `inspect`, `review-input`, `profile`, `template`, `schema`, `check`, `record-metadata`, `record-review`, `apply-patch`, `evidence-add`, `deliver` and `stop`. The AI writes and invokes these commands. Humans normally enter a prompt and read the result. The current task view returned by `collect` is reused directly; `record-metadata` checks and accepts one candidate envelope, and `deliver` rechecks before export. `check --candidate FILE` provides optional read-only diagnostics without making a duplicate bare metadata file. The old `generate/review/generate-review --candidate` CLI protocol has been replaced by explicit tools; the five natural-language capabilities remain.

### Repository layout and tests

```text
skills/oep-metadata/   Installable instructions, tools and pinned assets
examples/             Synthetic data and source declaration
tests/                Program regression tests
index*.html           English, Chinese and German guide entry pages
locales/              Guide translations and localized prompt resources
docs/                 Shared guide scripts, styles, workflow data and examples
```

```sh
uv run --locked --project skills/oep-metadata/scripts --group dev \
  python -m pytest tests -q
```

Tests exercise correction/retry, delivery gates, evidence binding, independent review attestation, repair scope, relocation and simulated upload protocols. They do not establish the accuracy of arbitrary AI claims. Generated `runs/`, caches and virtual environments are ignored by Git.
