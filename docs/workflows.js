window.OEP_WORKFLOWS = [
  {
    "id": "generate",
    "name": "Generate metadata",
    "short": "collect → accept → deliver",
    "tag": "01",
    "description": "The AI reads your material, chooses questions and tools, corrects errors, and delivers valid metadata with a short summary.",
    "prompt": "Use $oep-metadata to generate metadata from examples/capacity.csv using examples/capacity-source.md. Save to runs/draft-01. Correct program errors before delivery, retain unsupported unknowns and briefly explain material gaps. No independent review or upload.",
    "steps": [
      {
        "actor": "You → Host AI",
        "title": "State the goal",
        "body": "Give the agent one dataset and the relevant documents. The host AI selects tools and writes commands; you do not implement the protocol.",
        "inputs": "Dataset + documents + intended use",
        "outputs": "A scoped AI task",
        "gate": "Multiple background documents are welcome; one run generates one metadata document.",
        "example": "Use $oep-metadata to generate metadata from examples/capacity.csv\nusing examples/capacity-source.md. Save to runs/draft-01."
      },
      {
        "actor": "Host AI → Python",
        "title": "Collect evidence and observe structure",
        "body": "The AI calls collect. Python freezes inputs and returns the current generation view with one profile, evidence, hashes and a neutral template. Reuse that response; an unchanged inspect would repeat it.",
        "inputs": "One data source + repeated background arguments",
        "outputs": "Tool response: metadata template, profile, evidence IDs, hashes",
        "gate": "A neutral template is not an AI answer. No observed nulls does not establish a NOT NULL constraint.",
        "example": "collect --intent generate --data examples/capacity.csv\n  --background examples/capacity-source.md --out runs/draft-01"
      },
      {
        "actor": "Host AI ↔ You",
        "title": "Read first, ask what matters",
        "body": "The AI reads all supplied documentation, groups related gaps and asks only for decisive missing facts. If you answer, it registers a declaration and refreshes its context.",
        "inputs": "Evidence + your intended use",
        "outputs": "Necessary clarifications or explicit retained unknowns",
        "gate": "Empty optional schema fields do not each become a question.",
        "example": "If a decisive fact is missing, the AI asks first.\nRegister the answer only when supplied:\nevidence-add --out runs/draft-01\n  --file input/owner-declaration.md --kind declaration"
      },
      {
        "actor": "Host AI",
        "title": "Write one candidate envelope",
        "body": "The AI reads evidence and authors metadata with per-leaf provenance. One candidate file contains input_hash, metadata and provenance; the record tool checks it before acceptance.",
        "inputs": "Current generation view + source material",
        "outputs": "One metadata candidate envelope",
        "gate": "A separate bare metadata copy is unnecessary. Use check --candidate for a read-only diagnostic when needed.",
        "example": "{\"input_hash\":\"CURRENT_INPUT_HASH\",\"metadata\":{...},\"provenance\":[...]}\n\n# Optional field lookup:\nschema --pointer /resources/0/temporal/timeseries/0/start\n# Optional diagnostic using the same candidate envelope:\ncheck --candidate runs/draft-01/.work/authoring/candidate.json --run runs/draft-01"
      },
      {
        "actor": "Host AI → Python",
        "title": "Accept working metadata",
        "body": "The AI calls record-metadata to check and accept its candidate. It interprets rejection results and corrects errors before resubmission. Acceptance stores a working revision; the AI decides whether to deliver.",
        "inputs": "Current input_hash + metadata + provenance",
        "outputs": "Accepted working version + checks + refreshed hash\nOr rejection details for the AI to correct",
        "gate": "Mechanical rejection preserves working metadata and its hash. Final delivery rechecks the accepted document.",
        "example": "record-metadata --out runs/draft-01\n  --candidate runs/draft-01/.work/authoring/candidate.json"
      },
      {
        "actor": "Host AI → Python → You",
        "title": "Deliver two useful files",
        "body": "The AI writes a short summary of grouped actions and caveats, then explicitly calls deliver. Python rechecks the result before exporting it. If completion is impossible, the AI calls stop instead.",
        "inputs": "Accepted valid metadata + AI-authored summary",
        "outputs": "metadata.json + summary.md",
        "gate": "Acceptance and delivery are two validation gates. Missing essential facts can require an honest stop; unspecified optional facts remain explained in summary.md.",
        "example": "deliver --out runs/draft-01 --summary runs/draft-01/.work/authoring/summary-input.json\n# User reads: metadata.json and summary.md"
      }
    ],
    "route": [
      {
        "label": "collect",
        "step": 1,
        "detail": "Freeze evidence and return the current input."
      },
      {
        "label": "record-metadata",
        "step": 4,
        "detail": "Check the candidate and accept a working version."
      },
      {
        "label": "deliver",
        "step": 5,
        "detail": "Recheck and export metadata.json + summary.md."
      }
    ],
    "route_count": "3 core tool calls",
    "route_note": "Between these calls, the AI reads sources, asks only necessary questions and authors the candidate. A rejection returns to AI correction and resubmission.",
    "optional": [
      {
        "label": "schema --pointer",
        "detail": "Read one field specification when its meaning is unclear."
      },
      {
        "label": "check --candidate",
        "detail": "Use a separate read-only check when investigating a draft."
      },
      {
        "label": "evidence-add",
        "detail": "Register a material user declaration or new document."
      },
      {
        "label": "inspect",
        "detail": "Refresh a changed/resumed run; use --view full for internal diagnostics."
      }
    ]
  },
  {
    "id": "review",
    "name": "Review metadata",
    "short": "Check claims against evidence",
    "tag": "02",
    "description": "The AI evaluates current claims against evidence, records grouped findings and checks proposed corrections while preserving the original.",
    "prompt": "Use $oep-metadata to review input/metadata.json against input/data.csv and input/source.md. Save to runs/review-01. Show conflicts and meaningful uncertainty first, summarize user actions and keep the original unchanged. No upload.",
    "steps": [
      {
        "actor": "You → Host AI",
        "title": "Choose the reviewed document",
        "body": "Specify the metadata snapshot, optional data and source documents. The AI chooses how to investigate it.",
        "inputs": "Existing metadata + supporting material",
        "outputs": "A review task scoped to this snapshot",
        "gate": "Review can report errors in an invalid original; it does not imply successful metadata generation.",
        "example": "collect --intent review --metadata input/metadata.json\n  --data input/data.csv --background input/source.md --out runs/review-01"
      },
      {
        "actor": "Host AI → Python",
        "title": "Read checks and frozen evidence",
        "body": "The collect response already contains the reviewer view, original evidence, hashes, checks and populated targets. The AI reuses it and reads source material. Full diagnostics are available on demand.",
        "inputs": "Frozen metadata + evidence + available constraints",
        "outputs": "Checks and review targets",
        "gate": "Schema validity cannot establish a correct license or description.",
        "example": "collect response:\n  context.metadata + context.review_fields\n  context.profile + context.evidence + checks\n# Inspect again only when needed after a change."
      },
      {
        "actor": "Host AI ↔ You",
        "title": "Investigate meaningful uncertainty",
        "body": "The AI checks what could alter a finding and asks only for decisive missing evidence. Blank optional fields are not automatically questions.",
        "inputs": "Current claims + original sources",
        "outputs": "Supported judgments or explicit uncertainty",
        "gate": "Register substantive new facts before binding a review to them.",
        "example": "evidence-add --out runs/review-01\n  --file input/clarification.md --kind declaration"
      },
      {
        "actor": "Host AI",
        "title": "Assess each requested claim",
        "body": "The Reviewer writes supported, conflict, unknown or not_applicable decisions with reasons and evidence. Only conflicts can propose a replacement.",
        "inputs": "Current metadata + review targets + original evidence",
        "outputs": "Review candidate JSON",
        "gate": "Unknown is insufficient evidence, not a confirmed error. A missing fact alone is not not_applicable.",
        "example": "{\"pointer\":\"/resources/0/title\", \"decision\":\"conflict\",\n \"comment\":\"The source states another title.\",\n \"evidence_ids\":[\"CURRENT_EVIDENCE_ID\"], \"proposed_value\":\"Documented title\"}"
      },
      {
        "actor": "Host AI → Python",
        "title": "Check proposed corrections",
        "body": "The AI records the review and inspects checks for its suggested copy. It revises invalid suggestions before delivery; the original is preserved.",
        "inputs": "Current hashes + complete opinions",
        "outputs": "Agent decision counts + program decision counts\nSuggested-copy checks",
        "gate": "Invalid suggested metadata is never exported as a usable corrected document.",
        "example": "record-review --out runs/review-01\n  --candidate runs/review-01/.work/authoring/review-candidate.json"
      },
      {
        "actor": "Host AI → Python → You",
        "title": "Deliver findings and a brief summary",
        "body": "The AI groups actual actions and material limitations. The report shows conflicts and unknowns first, with other decisions collapsed and program checks included.",
        "inputs": "Recorded review + concise summary",
        "outputs": "review.md + summary.md; valid metadata.suggested.json when applicable",
        "gate": "The report identifies its target snapshot. A conflict in the original report does not mean the suggested copy still contains it.",
        "example": "deliver --out runs/review-01 --summary runs/review-01/.work/authoring/summary-input.json"
      }
    ],
    "route": [
      {
        "label": "collect",
        "step": 0,
        "detail": "Freeze the original and return review targets."
      },
      {
        "label": "record-review",
        "step": 4,
        "detail": "Record opinions and check the suggested copy."
      },
      {
        "label": "deliver",
        "step": 5,
        "detail": "Export review.md, summary.md and a valid suggestion when applicable."
      }
    ],
    "route_count": "3 core tool calls",
    "route_note": "The AI evaluates the existing claims against evidence. The report remains bound to that input; a suggested copy is a separate document.",
    "optional": [
      {
        "label": "schema --pointer",
        "detail": "Inspect a field meaning without reading the entire schema."
      },
      {
        "label": "evidence-add",
        "detail": "Register decisive supplementary evidence and refresh bindings."
      },
      {
        "label": "New review run",
        "detail": "Review the suggested copy separately when a new assessment is wanted."
      }
    ]
  },
  {
    "id": "generate-review",
    "name": "Generate, review & repair",
    "short": "A bounded independent loop",
    "tag": "03",
    "description": "The host AI coordinates generation, fresh independent reviews and evidence-backed repairs. Tools enforce acceptance and export contracts without scheduling roles.",
    "prompt": "Use $oep-metadata to generate metadata from input/data.csv and input/source.md, have a fresh independent agent review it, repair supported findings and obtain another fresh review after changes. Use at most two repair rounds. Save to runs/checked-01. Explain remaining limitations. No upload.",
    "steps": [
      {
        "actor": "Coordinator AI → Python",
        "title": "Collect the combined task",
        "body": "The coordinator freezes inputs and reads the tool response. It sets a correction budget and decides how to use its agents and tools.",
        "inputs": "Data + documents + intended use",
        "outputs": "Neutral working context and evidence",
        "gate": "Python never launches agents or tells the host which role to run next.",
        "example": "collect --intent generate-review --data input/data.csv\n  --background input/source.md --out runs/checked-01"
      },
      {
        "actor": "Generator AI → Python",
        "title": "Generate, check and accept",
        "body": "The Generator interprets the evidence, fixes check failures and records working metadata. Citations and validation do not guarantee that its interpretation is correct.",
        "inputs": "Neutral template + original material",
        "outputs": "Mechanically accepted working metadata",
        "gate": "The AI can ask for decisive facts and use multiple check/correction rounds.",
        "example": "record-metadata --out runs/checked-01\n  --candidate runs/checked-01/.work/authoring/candidate.json\n# The tool checks before accepting; the AI corrects any rejection."
      },
      {
        "actor": "Coordinator AI → fresh Reviewer",
        "title": "Request an independent assessment",
        "body": "The AI exports a current reviewer-input packet, then starts a fresh Reviewer with that packet and frozen source snapshots. The packet excludes generation provenance and prior opinions.",
        "inputs": "Isolated reviewer input + role instructions",
        "outputs": "A clean hash-bound Reviewer packet\nOne opinion per populated target",
        "gate": "The packet includes its candidate template, field contract, verified source snapshots and program-check coverage. The host supplies the fresh context.",
        "example": "review-input --out runs/checked-01\n# Host starts a fresh Reviewer with:\n# runs/checked-01/.work/reviewer-input.json\n# and its referenced frozen snapshots."
      },
      {
        "actor": "Coordinator AI → Python",
        "title": "Record the review and choose the next action",
        "body": "The AI records the actual independent candidate, reads separate agent/program counts and suggested-copy checks, then chooses a supported correction, a necessary question, delivery or an honest stop.",
        "inputs": "Conflicts + meaningful uncertainty + checks",
        "outputs": "A reasoned correction, clarification or stopping decision",
        "gate": "No code-driven transition chooses a Repair agent or automatically completes the task.",
        "example": "record-review --out runs/checked-01\n  --candidate runs/checked-01/.work/authoring/review-candidate.json --independent\n# The coordinator AI interprets the counts and chooses the next action."
      },
      {
        "actor": "Repair AI → Python",
        "title": "Apply an evidence-backed correction",
        "body": "The coordinator or a Repair agent authors a scoped patch. Python checks old values, reviewed scope, evidence and the entire result.",
        "inputs": "Current hashes + findings + source evidence",
        "outputs": "Accepted revision or rejection for the AI to interpret",
        "gate": "Accepted changes invalidate the review. Repeated versions are refused.",
        "example": "apply-patch --out runs/checked-01\n  --candidate runs/checked-01/.work/authoring/patch-candidate.json"
      },
      {
        "actor": "Coordinator AI → new Reviewer",
        "title": "Check and review again",
        "body": "After a change or new evidence, the coordinator obtains a fresh independent review. It stops on no progress, insufficient evidence or exhausted resources.",
        "inputs": "Revised current metadata + refreshed context",
        "outputs": "A current review bound to this version and evidence",
        "gate": "Reusing an earlier Reviewer answer is not a fresh independent review.",
        "example": "review-input --out runs/checked-01\n# Host starts a new Reviewer using the refreshed clean packet.\nrecord-review --out runs/checked-01 --candidate FILE --independent"
      },
      {
        "actor": "Coordinator AI → Python → You",
        "title": "Choose delivery or an honest stop",
        "body": "The AI explicitly delivers only with passing checks and a current independent review with no conflicts. It groups remaining uncertainty in a short summary.",
        "inputs": "Valid metadata + current review + AI summary",
        "outputs": "metadata.json + review.md + summary.md; or summary.md only on stop",
        "gate": "Mechanical validity and agent agreement do not prove factual accuracy.",
        "example": "deliver --out runs/checked-01 --summary runs/checked-01/.work/authoring/summary-input.json\n# If blocked instead: stop --out runs/checked-01 --summary FILE"
      }
    ],
    "route": [
      {
        "label": "collect",
        "step": 0,
        "detail": "Freeze data and documents."
      },
      {
        "label": "record-metadata",
        "step": 1,
        "detail": "Check and accept the generated candidate."
      },
      {
        "label": "review-input",
        "step": 2,
        "detail": "Export a clean current Reviewer packet."
      },
      {
        "label": "record-review",
        "step": 3,
        "detail": "Record a fresh independent assessment."
      },
      {
        "label": "deliver",
        "step": 6,
        "detail": "Recheck this version and export the reviewed result."
      }
    ],
    "route_count": "5 core calls before any repair",
    "route_note": "The host AI starts the fresh Reviewer and decides whether to repair. Each accepted change needs a new packet and another fresh independent review before delivery.",
    "optional": [
      {
        "label": "apply-patch",
        "detail": "Apply only evidence-backed reviewed changes, then obtain a fresh review."
      },
      {
        "label": "evidence-add",
        "detail": "Add decisive new evidence; the old review becomes stale."
      },
      {
        "label": "stop",
        "detail": "Explain missing evidence, unavailable isolation, exhausted budget or lack of progress."
      }
    ]
  },
  {
    "id": "metadata-upload",
    "name": "Upload metadata",
    "short": "Plan, execute, verify",
    "tag": "04",
    "description": "Update metadata on an existing OEP table through a separately authorized operation. The plan binds the candidate and target; execution rechecks the platform before writing.",
    "prompt": "Use $oep-metadata to prepare a metadata upload plan for input/metadata.json to existing table your_table at https://openenergyplatform.org. Save the backup, diff and plan to runs/upload-01. Do not execute.",
    "steps": [
      {
        "title": "Choose the exact update",
        "actor": "You",
        "body": "Select the metadata file, existing table and OEP origin. Specify plan-only or authorize execution of a concrete plan. Data-row upload, table creation and publication are separate operations.",
        "inputs": "Metadata JSON + target origin/table",
        "outputs": "A precisely scoped upload request",
        "gate": "Generating a local metadata document does not authorize a remote write.",
        "example": "metadata-upload --metadata input/metadata.json\n  --table your_table --out runs/upload-01"
      },
      {
        "title": "Validate and inspect remote state",
        "actor": "Host AI → CLI + Python",
        "body": "Validate metadata before preparing the upload. Read the current remote metadata and inspect the table’s Open Peer Review status. Record unknown status rather than treating it as inactive.",
        "inputs": "Candidate + current OEP state",
        "outputs": "Remote snapshot + review status",
        "gate": "Only confirmed inactive review status makes a plan executable.",
        "example": "active → blocked\nunverified → blocked\ninactive → eligible for further checks"
      },
      {
        "title": "Save a reviewable plan",
        "actor": "Python",
        "body": "Write the remote backup, upload candidate and readable diff. Bind the target, candidate hash, remote hash, status and plan hash. Persist relative output references.",
        "inputs": "Local candidate + remote snapshot",
        "outputs": "metadata.remote.backup.json · metadata.diff\nmetadata.upload.json · upload.plan.json",
        "gate": "A prepared plan has not sent a metadata POST.",
        "example": "Plan fields:\noperation · base_url · table\npayload_hash · remote_hash · review_status\nexecutable · plan_hash"
      },
      {
        "title": "Authorize and bind execution",
        "actor": "You + Host AI → CLI",
        "body": "Inspect the diff and target. Execute the selected plan with the matching metadata, table and output directory. The API token comes from a named environment variable. The plan file’s location binds its directory at runtime.",
        "inputs": "Authorized plan + API token in environment",
        "outputs": "A verified local plan and candidate binding",
        "gate": "A stale candidate, changed plan hash or mismatched output directory is rejected.",
        "example": "metadata-upload --metadata input/metadata.json\n  --table your_table --out runs/upload-01\n  --execute --plan runs/upload-01/upload.plan.json"
      },
      {
        "title": "Recheck and write once",
        "actor": "Python + OEP",
        "body": "Recheck that peer review is inactive and the remote metadata still matches the planned snapshot. Create an exclusive attempt marker before POSTing the candidate. Never automatically retry an uncertain attempt.",
        "inputs": "Current remote state + bound plan",
        "outputs": "One attempted metadata update",
        "gate": "Client prechecks are not an atomic server-side conditional write.",
        "example": "Recheck status → compare remote hash\n→ claim upload.attempt.json → POST metadata"
      },
      {
        "title": "Read back and record the result",
        "actor": "Python",
        "body": "Read the stored metadata back. Compare it with the write response and requested candidate. Record a verified result, server-side changes, or an uncertain outcome requiring inspection.",
        "inputs": "Write response + readback",
        "outputs": "metadata.readback.json · upload.receipt.json",
        "gate": "An HTTP success alone is not verification. Production writes remain unverified by this project.",
        "example": "verified\nstored_with_server_changes\nnot_verified_do_not_retry"
      }
    ],
    "route": [
      {
        "label": "metadata-upload",
        "step": 0,
        "detail": "Validate and prepare a target-bound backup/diff/plan."
      },
      {
        "label": "Inspect plan",
        "step": 2,
        "detail": "The AI and user inspect the concrete proposed update."
      },
      {
        "label": "metadata-upload --execute",
        "step": 4,
        "detail": "Execute the user-authorized target and action."
      },
      {
        "label": "Read-back receipt",
        "step": 5,
        "detail": "Verify the remote result and report the receipt."
      }
    ],
    "route_count": "Prepare → inspect → authorized execution",
    "route_note": "The AI interprets the plan and the existing authorization. Preparation and execution recheck remote state; verification is part of a successful upload.",
    "optional": [
      {
        "label": "check",
        "detail": "Investigate local metadata errors before preparing an upload."
      },
      {
        "label": "New plan",
        "detail": "Prepare a fresh plan when payload or remote state changed."
      }
    ]
  },
  {
    "id": "review-upload",
    "name": "Save or submit review",
    "short": "Local opinions to OEP fields",
    "tag": "05",
    "description": "Translate a finalized local review into the platform’s existing Open Peer Review protocol. Saving, submitting and granting a badge are different actions.",
    "prompt": "Use $oep-metadata to prepare a plan to save the recorded opinions from runs/review-01 as a new Open Peer Review draft for table your_table at https://openenergyplatform.org. Use its matching snapshot and my authorized session-cookie file. Save to runs/review-save-01 without executing.",
    "steps": [
      {
        "title": "Select snapshot, opinions and action",
        "actor": "You",
        "body": "Provide a finalized review and its matching metadata snapshot. Choose save or submit and the existing review ID when applicable. Supply an authorized session-cookie file separately.",
        "inputs": "Metadata + bound review JSON + table/action",
        "outputs": "A specific save or submit request",
        "gate": "An API token is not a substitute for an authenticated web session.",
        "example": "review-upload --metadata runs/review-01/.work/original.metadata.json\n  --review runs/review-01/.work/review.json --table your_table\n  --action save --out runs/review-save-01\n  --cookies \"$OEP_COOKIE_FILE\""
      },
      {
        "title": "Check account role and snapshot",
        "actor": "Python + OEP",
        "body": "Verify that the local review matches the selected metadata hash. Read the platform page, confirm reviewer access and turn, and compare platform-exposed resource fields with the local snapshot.",
        "inputs": "Local review + authenticated platform page",
        "outputs": "A verified field mapping and page state",
        "gate": "A subagent is not a second platform identity. Contributor/reviewer separation still applies.",
        "example": "Local metadata hash = review metadata_hash\nLocal resource fields = OEP frozen fields\nAccount role and current turn allow review"
      },
      {
        "title": "Map supported field opinions",
        "actor": "Python",
        "body": "Map supported to Accept, conflict with a replacement to Suggest, and conflict without one to Deny. Do not turn unknown or not_applicable into approvals. Report skipped fields and reject unsupported edits.",
        "inputs": "Field-level opinions + platform field keys",
        "outputs": "OPR payload + mapped and skipped opinions",
        "gate": "Submit needs explicit coverage of every filled platform field. All-Accept finish/badge handling is outside this adapter.",
        "example": "supported → Accept\nconflict + proposed text → Suggest\nconflict without replacement → Deny\nunknown / not_applicable → unresolved"
      },
      {
        "title": "Prepare and inspect the plan",
        "actor": "Python + You",
        "body": "Save a parsed remote backup, prepared payload and hash-bound upload plan. Check which opinions can be expressed and whether the intended action is save or submit. Raw HTML and session credentials are not copied into these artifacts.",
        "inputs": "Mapped payload + remote fingerprint",
        "outputs": "opr.remote.backup.json · opr.upload.json\nupload.plan.json",
        "gate": "A save can retain an incomplete draft; unresolved required opinions block submit.",
        "example": "Review target binding:\norigin · table · review_id · action\nmetadata_hash · entries_hash\nremote_hash · payload_hash · plan_hash"
      },
      {
        "title": "Execute the authorized action",
        "actor": "Host AI → CLI + Python + OEP",
        "body": "Repeat the same table, action, review ID and output directory. Recheck role, turn, snapshot and field history, then send one CSRF-authenticated request. For a new save, discover the review ID returned through the platform page rather than guessing it.",
        "inputs": "Authorized plan + web session",
        "outputs": "One save or submit attempt",
        "gate": "Keep the cookie file outside run artifacts. An uncertain attempt must be inspected before retry.",
        "example": "review-upload --metadata runs/review-01/.work/original.metadata.json\n  --review runs/review-01/.work/review.json --table your_table\n  --action save --out runs/review-save-01\n  --cookies \"$OEP_COOKIE_FILE\" --execute\n  --plan runs/review-save-01/upload.plan.json"
      },
      {
        "title": "Verify opinions and turn transition",
        "actor": "Python + You",
        "body": "Read the review back and compare expected field contributions and state. Submission must confirm the turn transition; saving must retain the expected editable turn. To submit a newly saved draft, prepare a separate plan with its verified review ID.",
        "inputs": "Readback history + platform state",
        "outputs": "opr.readback.json · upload.receipt.json",
        "gate": "No badge, finish operation or platform certification is implied. Live production behavior remains unverified.",
        "example": "Save new draft → discover verified ID\n→ prepare a new submit plan with that ID\n→ separately authorize and execute submit"
      }
    ],
    "route": [
      {
        "label": "review-upload",
        "step": 0,
        "detail": "Prepare the selected save or submit action."
      },
      {
        "label": "Inspect mapping",
        "step": 2,
        "detail": "Check the role, frozen snapshot and opinion mapping."
      },
      {
        "label": "review-upload --execute",
        "step": 4,
        "detail": "Execute the user-authorized action."
      },
      {
        "label": "Read-back receipt",
        "step": 5,
        "detail": "Verify saved opinions and platform status."
      }
    ],
    "route_count": "Save and submit are separate actions",
    "route_note": "The AI uses the matching metadata snapshot and machine-readable opinions. A save plan does not itself submit a review or grant a platform badge.",
    "optional": [
      {
        "label": "save",
        "detail": "Save incomplete working opinions where the adapter allows it."
      },
      {
        "label": "submit",
        "detail": "Prepare a separate submit plan for the authorized verified review ID."
      }
    ]
  }
];
