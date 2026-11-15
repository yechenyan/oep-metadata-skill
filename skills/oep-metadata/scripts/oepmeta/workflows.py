"""Agent-invoked tools. The host chooses every action; Python enforces contracts."""

import copy
import html
import json
import re
import shutil
from pathlib import Path

from .common import (SKILL_ROOT, WorkflowError, empty, file_hash, get_pointer,
                     json_hash, leaves, load_json, now, parts, set_pointer, write_json)

INTENTS = {"generate", "review", "generate-review"}
DECISIONS = {"supported", "conflict", "unknown", "not_applicable"}


def _validation(metadata, context, out):
    from .validate import validate_metadata
    index = Path(out) / context["ontology_index"] if context.get("ontology_index") else None
    return validate_metadata(metadata, profile=context.get("profile"),
                             db_schema=context.get("db_schema"), ontology_index=index)


def _text(value):
    value = html.escape(str(value), quote=False)
    value = re.sub(r"([\\`*_[\]|~])", r"\\\1", value)
    value = re.sub(r"(?m)^([ \t]*)([#+=\-])", r"\1\\\2", value)
    return re.sub(r"(?m)^([ \t]*\d{1,9})([.)])(?=[ \t])", r"\1\\\2", value)


def _code(value):
    return "<code>" + html.escape(str(value)) + "</code>"


def _write_text(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")

def _known_ids(context):
    return {item["id"] for item in context["evidence"]}

def _check_evidence(ids, context, required=False):
    if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
        raise WorkflowError("evidence_ids must be a list of evidence IDs")
    if set(ids) - _known_ids(context):
        raise WorkflowError("Unknown evidence IDs: " + ", ".join(sorted(set(ids) - _known_ids(context))))
    if required and not ids:
        raise WorkflowError("A supported claim or proposed change requires evidence")

def _auto_entries(metadata, context):
    """Only observed column names and pinned version are mechanically accepted."""
    known_columns = set((context.get("profile") or {}).get("columns", {}))
    if context.get("db_schema"):
        known_columns |= set(context["db_schema"].get("columns", {}))
    resources = metadata.get("resources")
    if not isinstance(resources, list) or len(resources) != 1:
        known_columns = set()
    evidence_ids = [item["id"] for item in context["evidence"] if item.get("kind") in {"data_profile", "profile", "db_schema", "schema"}]
    entries = []
    for pointer, value in leaves(metadata):
        if (re.fullmatch(r"/resources/\d+/schema/fields/\d+/name", pointer) and isinstance(value, str) and value in known_columns) or (pointer == "/metaMetadata/metadataVersion" and value == "OEMetadata-2.0.4"):
            entries.append({"pointer": pointer, "decision": "supported", "comment": "Observed column name or pinned target version verified by the program; no semantic acceptance is implied for other fields.", "evidence_ids": evidence_ids, "origin": "program"})
    return entries

def _context_fields(metadata, context):
    auto = _auto_entries(metadata, context)
    auto_paths = {entry["pointer"] for entry in auto}
    schema = load_json(SKILL_ROOT / "assets" / "oemetadata-2.0.4" / "schema.json")
    def specification(pointer):
        current = schema
        for token in parts(pointer):
            if not isinstance(current, dict):
                return {}
            if token.isdigit():
                current = current.get("items", {})
            else:
                current = current.get("properties", {}).get(token, {})
        return {key: current[key] for key in ("description", "type", "format", "enum", "examples") if key in current}
    fields = [{"pointer": p, "value": v, "specification": specification(p)} for p, v in leaves(metadata) if not empty(v) and p not in auto_paths]
    return fields, auto

def _semantic_provenance(metadata, original, entries, context):
    if not isinstance(entries, list):
        raise WorkflowError("provenance must be a list")
    by_pointer = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise WorkflowError("Malformed provenance entry")
        pointer = entry.get("pointer")
        get_pointer(metadata, pointer)
        if pointer in by_pointer:
            raise WorkflowError("Duplicate provenance pointer")
        status = entry.get("status")
        if status not in {"supported", "unknown", "not_applicable"}:
            raise WorkflowError("Invalid provenance status")
        _check_evidence(entry.get("evidence_ids", []), context, required=status == "supported")
        if not isinstance(entry.get("rationale"), str) or not entry["rationale"].strip():
            raise WorkflowError("Provenance needs a rationale")
        value = get_pointer(metadata, pointer)
        if status == "unknown" and not (empty(value) or value == "ToDo"):
            raise WorkflowError(f"Unknown claim contains a concrete value: {pointer}")
        if status == "not_applicable" and value is not None:
            raise WorkflowError("not_applicable must export as JSON null")
        by_pointer[pointer] = entry
    original_leaves = dict(leaves(original))
    for pointer, value in leaves(metadata):
        if original_leaves.get(pointer, object()) == value or empty(value) or value == "ToDo":
            continue
        entry = by_pointer.get(pointer)
        if not entry or entry["status"] != "supported":
            raise WorkflowError(f"Changed populated field requires supported provenance: {pointer}")
        # Data profiles cannot establish the rights holder, author, or a data license.
        if re.search(r"/(licenses|sourceLicenses|contributors|authors)/|/metaMetadata/metadataLicense/|/context/(contact|publisher)", pointer) or (pointer.endswith("/nullable") and value is False):
            facts = {item["id"]: item for item in context["evidence"]}
            kinds = {facts[eid].get("kind") for eid in entry["evidence_ids"]}
            if not kinds.intersection({"background", "document", "declaration", "source"}):
                raise WorkflowError(f"Identity, license or non-null constraint needs documentary or declared evidence: {pointer}")
    return copy.deepcopy(entries)

def _guard_structure(metadata, original):
    if metadata.get("metaMetadata", {}).get("metadataVersion") != "OEMetadata-2.0.4":
        raise WorkflowError("Generation/repair cannot change the target metadata version")
    current_resources = metadata.get("resources")
    original_resources = original.get("resources", [])
    if not isinstance(current_resources, list) or len(current_resources) != len(original_resources):
        raise WorkflowError("Generation/repair cannot change resource count")
    for current, previous in zip(current_resources, original_resources):
        if not isinstance(current, dict) or not isinstance(current.get("schema"), dict):
            raise WorkflowError("Each generated resource requires a schema object")
        current_fields = current.get("schema", {}).get("fields", [])
        previous_fields = previous.get("schema", {}).get("fields", [])
        if not isinstance(current_fields, list) or any(not isinstance(field, dict) for field in current_fields):
            raise WorkflowError("Generated schema fields must be objects")
        if len(current_fields) != len(previous_fields):
            raise WorkflowError("Generation/repair cannot change the observed field count")
        for key in ("name", "type"):
            if any(field.get(key) != old.get(key) and (key == "name" or old.get(key) is not None) for field, old in zip(current_fields, previous_fields)):
                raise WorkflowError(f"Generation/repair cannot alter observed field names/order or declared database {key} values")

def _check_review(context, result):
    if result.get("metadata_hash") != context["metadata_hash"]:
        raise WorkflowError("Review metadata_hash does not match this draft")
    entries = result.get("entries")
    if not isinstance(entries, list):
        raise WorkflowError("Review entries must be a list")
    expected = {field["pointer"] for field in context["review_fields"]}
    received = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise WorkflowError("Malformed review entry")
        pointer = entry.get("pointer")
        if pointer in received or pointer not in expected:
            raise WorkflowError(f"Unexpected or duplicate review pointer: {pointer}")
        received.add(pointer)
        if entry.get("decision") not in DECISIONS:
            raise WorkflowError(f"Invalid review decision: {pointer}")
        if not isinstance(entry.get("comment"), str) or not entry["comment"].strip():
            raise WorkflowError(f"Review comment required: {pointer}")
        _check_evidence(entry.get("evidence_ids", []), context, required=entry["decision"] in {"supported", "conflict"} or "proposed_value" in entry)
        if "proposed_value" in entry and entry["decision"] != "conflict":
            raise WorkflowError("Only a conflict may propose a replacement")
    if expected - received:
        raise WorkflowError("Missing review pointers: " + ", ".join(sorted(expected - received)[:20]))
    agent_entries = [{**copy.deepcopy(entry), "origin": "agent"} for entry in entries]
    return agent_entries + copy.deepcopy(context["auto_entries"])

def review_decision_counts(entries):
    return {decision: sum(entry["decision"] == decision for entry in entries)
            for decision in ("conflict", "unknown", "supported", "not_applicable")}

def render_review_report(review):
    """Render model text literally and separate attention from confirmed items."""
    counts = review_decision_counts(review["entries"])
    lines = ["# Metadata review", "", "Reviewed target (canonical JSON SHA-256): " + _code(review["metadata_hash"]), "",
             _text(review.get("summary", "")), "", "## Decision summary", "",
             "| Decision | Count | Action |", "| --- | ---: | --- |"]
    actions = {"conflict": "Inspect or correct", "unknown": "Supply evidence or retain uncertainty",
               "supported": "Usually no action within scope", "not_applicable": "No action if justified"}
    for decision, count in counts.items():
        lines.append(f"| `{decision}` | {count} | {actions[decision]} |")
    lines += ["", f"Field decisions needing attention: **{counts['conflict'] + counts['unknown']}**. "
              "Unknown is not a confirmed error. These categories are not severity scores."]
    automatic = sum(e.get("origin") == "program" for e in review["entries"])
    lines += ["", f"Agent judgments: {len(review['entries']) - automatic}; automatic checks: {automatic}. "
              "Decisions cover populated claims; unspecified optional facts may remain in the summary."]
    checks = review.get("checks", {})
    errors = [i for i in checks.get("issues", []) if i.get("severity") == "error"]
    warnings = [i for i in checks.get("issues", []) if i.get("severity") == "warning"]
    lines += ["", "## Program checks", "", f"{len(errors)} errors; {len(warnings)} warnings. "
              "Mechanical validity does not establish factual correctness."]
    for issue in errors + warnings:
        lines.append("- " + _code(issue.get("severity")) + " " + _code(issue.get("pointer", "")) + ": " + _text(issue.get("message", "")))
    for decision, title, folded in (("conflict", "Conflicts - inspect or correct", False),
                                     ("unknown", "Unresolved - needs evidence", False),
                                     ("supported", "Evidence-supported", True),
                                     ("not_applicable", "Not applicable", True)):
        group = sorted((e for e in review["entries"] if e["decision"] == decision), key=lambda e: e["pointer"])
        lines += ["", f"## {title} ({len(group)})", ""]
        if folded:
            lines += ["<details>", f"<summary>Show {len(group)} field decisions</summary>", ""]
        if not group:
            lines.append("No field decisions in this group.")
        for entry in group:
            lines.append("- " + _code(entry["pointer"]) + f" - **{decision}**: " + _text(entry["comment"]))
            if "proposed_value" in entry:
                lines += ["", "  Suggested value: " + _code(json.dumps(entry["proposed_value"], ensure_ascii=False))]
            if entry.get("evidence_ids"):
                lines += ["", "  Evidence: " + ", ".join(_code(e) for e in entry["evidence_ids"])]
        if folded:
            lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def _save(out, context, state):
    context = copy.deepcopy(context)
    context["metadata_hash"] = json_hash(context["metadata"])
    context["review_fields"], context["auto_entries"] = _context_fields(context["metadata"], context)
    context.pop("input_hash", None)
    context["input_hash"] = json_hash(context)
    state.update(input_hash=context["input_hash"], metadata_hash=context["metadata_hash"], updated_at=now())
    write_json(Path(out) / ".work/context.json", context)
    write_json(Path(out) / ".work/state.json", state)
    return context


def _load(out, *, writable=False):
    out = Path(out).resolve()
    state = load_json(out / ".work/state.json")
    context = load_json(out / ".work/context.json")
    if state.get("protocol") != 2:
        raise WorkflowError("Legacy run: start a new agent-tool run")
    if writable and state["status"] != "open":
        raise WorkflowError("Run is closed; create a new run")
    digest = json_hash({k: v for k, v in context.items() if k != "input_hash"})
    if digest != state["input_hash"] or digest != context.get("input_hash"):
        raise WorkflowError("Context changed outside the tools")
    if json_hash(context["metadata"]) != state["metadata_hash"]:
        raise WorkflowError("Metadata changed outside the tools")
    for snapshot in context["snapshots"]:
        path = out / snapshot["path"]
        if not path.resolve().is_relative_to(out) or file_hash(path) != snapshot["sha256"]:
            raise WorkflowError("An evidence snapshot changed")
    return out, state, context


def _candidate(out, candidate):
    out, state, context = _load(out, writable=True)
    value = load_json(candidate) if isinstance(candidate, (str, Path)) else copy.deepcopy(candidate)
    if not isinstance(value, dict) or value.get("input_hash") != state["input_hash"]:
        raise WorkflowError("Candidate does not match current input_hash; inspect the run again")
    return out, state, context, value


def _task_view(result, view):
    if view == "full":
        return result
    context = result["context"]
    if view == "auto":
        view = "reviewer" if context["intent"] == "review" else "generation"
    if view not in {"generation", "reviewer", "status"}:
        raise WorkflowError("Unknown view; use auto, generation, reviewer, status or full")
    state = {key: result["state"][key] for key in
             ("intent", "status", "revision", "attempts", "max_changes", "outcome", "outputs")
             if key in result["state"]}
    response = {"ok": True, "view": view, "state": state, "checks": result["checks"],
                "paths": {"context_from_run": ".work/context.json",
                          "schema_from_skill": "assets/oemetadata-2.0.4/schema.json"}}
    if view == "status":
        response.update(input_hash=context["input_hash"], metadata_hash=context["metadata_hash"])
        if result["review"]:
            response["review_counts"] = result["review"]["decision_counts"]
        return response
    selected = copy.deepcopy({key: context[key] for key in
                             ("intent", "input_hash", "metadata_hash", "target_schema", "metadata", "profile",
                              "db_schema", "evidence", "snapshots", "ontology_index")})
    for evidence in selected["evidence"]:
        for kind, key in (("data_profile", "profile"), ("db_schema", "db_schema")):
            if evidence.get("kind") == kind and evidence.get("content") == selected.get(key):
                evidence.pop("content")
                evidence["content_ref"] = "/context/" + key
    if view == "reviewer":
        selected["review_fields"] = copy.deepcopy(context["review_fields"])
        for field in selected["review_fields"]:
            field["specification"].pop("examples", None)
        response["program_verified_count"] = len(context["auto_entries"])
        response["program_verified_pointers"] = [entry["pointer"] for entry in context["auto_entries"]]
        response["candidate_keys"] = result["contracts"]["review"]
    else:
        response["candidate_keys"] = result["contracts"]["metadata"]
    response["context"] = selected
    return response


def inspect(out, *, view="full"):
    out, state, context = _load(out)
    review = _current_review(out, state, context)
    result = {"ok": True, "state": state, "context": context, "review": review,
            "checks": _validation(context["metadata"], context, out),
            "contracts": {"metadata": ["input_hash", "metadata", "provenance"],
                          "review": ["input_hash", "metadata_hash", "entries", "summary"],
                          "patch": ["input_hash", "base_hash", "patches"],
                          "summary": {"overview": "Short outcome", "needs_attention": [], "notes": []}},
            "scope": "Tool result only. The host AI chooses the next action."}
    return _task_view(result, view)


def reviewer_input(out):
    """Export current evidence and targets without generation or prior opinions."""
    packet = inspect(out, view="reviewer")
    packet["role_instructions"] = (SKILL_ROOT / "references/roles/reviewer.md").read_text(encoding="utf-8")
    packet["candidate_template"] = {
        "input_hash": packet["context"]["input_hash"],
        "metadata_hash": packet["context"]["metadata_hash"],
        "summary": "Short assessment of this target and supplied evidence.",
        "entries": [],
    }
    packet["entry_contract"] = {
        "coverage": "Exactly one entry per context.review_fields pointer; program checks are added separately.",
        "required_keys": ["pointer", "decision", "comment", "evidence_ids"],
        "decisions": sorted(DECISIONS),
        "evidence": "Use registered IDs. Supported/conflict opinions and proposed changes require evidence.",
        "proposed_value": "Optional replacement for conflicts only; omit it when evidence cannot establish a replacement.",
        "hashes": "Use candidate_template hashes; compute metadata_hash over canonical JSON, not file bytes.",
    }
    packet["evidence_layout"] = {
        "content_ref": "JSON Pointer into this packet; original source snapshots remain available.",
        "original_filename": "Collection-supplied filename evidence; remote collections may use snapshot labels.",
    }
    packet["source_integrity"] = {
        "snapshot_hashes_verified_by_tool": True,
        "scope": "Verified at export and rechecked when recording; the Reviewer may verify independently.",
    }
    packet["path_bases"] = {"snapshots": "run directory (parent of this packet's .work directory)",
                            "schema_from_skill": "directory containing the loaded SKILL.md"}
    packet["packet_hash"] = json_hash(packet)
    target = Path(out) / ".work/reviewer-input.json"
    write_json(target, packet)
    return {"ok": True, "packet_from_run": ".work/reviewer-input.json", "packet_hash": packet["packet_hash"],
            "input_hash": packet["context"]["input_hash"], "metadata_hash": packet["context"]["metadata_hash"],
            "review_target_count": len(packet["context"]["review_fields"]),
            "program_verified_count": packet["program_verified_count"]}


def collect(intent, out, *, data=None, metadata=None, table=None, background=(),
            base_url="https://openenergyplatform.org", max_rows=None, ontology_index=None, max_changes=8, view="full"):
    from .collect import collect_inputs
    from .validate import build_skeleton
    if intent not in INTENTS or isinstance(max_changes, bool) or not 1 <= max_changes <= 30:
        raise WorkflowError("Invalid intent or max_changes (1-30)")
    if intent == "review" and not (metadata or table):
        raise WorkflowError("Review collection requires metadata or an OEP table")
    if intent != "review" and (metadata or not (data or table)):
        raise WorkflowError("Generation requires data or table and excludes existing metadata")
    out = Path(out).resolve()
    if out.exists() and any(out.iterdir()):
        raise WorkflowError("Output directory must be new and empty")
    out.mkdir(parents=True, exist_ok=True)
    collected = collect_inputs(data=data, metadata=metadata, table=table, background=background,
                               base_url=base_url, max_rows=max_rows, output_dir=out / ".work/inputs",
                               include_metadata=intent == "review")
    sources = {}
    for snapshot in collected["snapshots"]:
        previous = snapshot["path"]
        snapshot["path"] = (Path(".work/inputs") / previous).as_posix()
        if snapshot.get("source") == previous:
            sources[previous] = snapshot["path"]
            snapshot["source"] = snapshot["path"]
    if collected.get("profile"):
        old = collected["profile"].get("source")
        collected["profile"]["source"] = sources.get(old, old)
    for entry in collected["evidence"]:
        entry["source"] = sources.get(entry["source"], entry["source"])
        entry["id"] = "ev-" + json_hash({k: entry[k] for k in ("kind", "content", "source")})[:16]
    evidence = collected["evidence"]
    evidence.append({"id": "target-schema", "kind": "schema", "source": "assets/oemetadata-2.0.4/schema.json",
                     "content": "Pinned OEMetadata-2.0.4; schema checks do not establish semantic facts."})
    database = (collected.get("db_schema") or {}).get("columns", {})
    if isinstance(database, list):
        database = {column["name"]: column for column in database}
        collected["db_schema"]["columns"] = database
    if intent == "review":
        initial = collected["metadata"]
        if not isinstance(initial, dict):
            raise WorkflowError("Review metadata must be a JSON object")
    else:
        profile = copy.deepcopy(collected["profile"])
        if database:
            names = sorted(database, key=lambda n: database[n].get("ordinal_position", list(database).index(n)))
            profile["columns"] = {n: profile["columns"].get(n, {"type": "unknown", "null_count": 0, "nullable": None}) for n in names}
        initial = build_skeleton(profile, table_name=table or Path(data).stem,
                                 table_url=f"{base_url.rstrip('/')}/database/tables/{table}" if table else None)
        for field in initial["resources"][0]["schema"]["fields"]:
            declared = database.get(field["name"], {})
            if declared.get("data_type") or declared.get("type"):
                field["type"] = declared.get("data_type", declared.get("type"))
            nullable = declared.get("is_nullable", declared.get("nullable"))
            if isinstance(nullable, str) and nullable.upper() in {"YES", "NO"}:
                nullable = nullable.upper() == "YES"
            if isinstance(nullable, bool):
                field["nullable"] = nullable
    if ontology_index:
        target = out / ".work/inputs/ontology-index.json"
        shutil.copyfile(ontology_index, target)
        ontology_index = target.relative_to(out).as_posix()
        collected["snapshots"].append({"kind": "ontology_index", "path": ontology_index, "sha256": file_hash(target)})
        evidence.append({"id": "frozen-ontology", "kind": "ontology", "source": ontology_index,
                         "content": {"sha256": file_hash(target), "version": load_json(target).get("version")}})
    structure = None if intent == "review" else {"resources": [{"schema": {"fields": [
        {"name": f.get("name"), "type": database.get(f["name"], {}).get("data_type",
          database.get(f["name"], {}).get("type"))} for f in r["schema"]["fields"]]}}
        for r in initial["resources"]]}
    context = {"intent": intent, "metadata": initial, "structure": structure, "profile": collected.get("profile"),
               "db_schema": collected.get("db_schema"), "evidence": evidence,
               "snapshots": collected["snapshots"], "ontology_index": ontology_index,
               "target_schema": "OEMetadata-2.0.4"}
    state = {"protocol": 2, "intent": intent, "status": "open", "revision": 0, "created_at": now(),
             "max_changes": max_changes, "attempts": 0, "seen_hashes": [json_hash(initial)]}
    _save(out, context, state)
    write_json(out / ".work/original.metadata.json", initial)
    return inspect(out, view=view)


def check(metadata, *, out=None, profile=None, db_schema=None, ontology_index=None, candidate=False):
    from .validate import validate_metadata
    value = load_json(metadata) if isinstance(metadata, (str, Path)) else metadata
    envelope = isinstance(value, dict) and "resources" not in value and "metadata" in value
    if candidate and not envelope:
        raise WorkflowError("--candidate expects an object containing metadata; use --metadata for a bare document")
    if envelope:
        if not isinstance(value["metadata"], dict):
            raise WorkflowError("Candidate metadata must be a JSON object")
        value = value["metadata"]
    if out:
        out, _, context = _load(out)
        result = _validation(value, context, out)
    else:
        result = validate_metadata(value, profile=profile, db_schema=db_schema, ontology_index=ontology_index)
    return {"ok": result.get("mechanical_valid", False), "checks": result,
            "input_kind": "candidate" if envelope else "metadata"}


def _accept_metadata(out, state, context, value, provenance, agent=None):
    if state["attempts"] >= state["max_changes"]:
        return {"ok": False, "error": "change_limit", "message": "Host must stop or create a new run."}
    checks = _validation(value, context, out)
    if not checks.get("mechanical_valid", False):
        state["attempts"] += 1
        write_json(out / ".work/state.json", state)
        return {"ok": False, "checks": checks, "message": "Not accepted; the AI may correct and resubmit against the same input_hash."}
    previous = context["metadata"]
    digest = json_hash(value)
    if state["revision"] and digest in state["seen_hashes"]:
        return {"ok": False, "error": "no_progress_or_repeated_version"}
    retained = []
    for entry in context.get("provenance", []):
        try:
            if get_pointer(previous, entry["pointer"]) == get_pointer(value, entry["pointer"]):
                retained.append(entry)
        except WorkflowError:
            pass
    merged = {entry["pointer"]: entry for entry in retained + provenance}
    context.update(metadata=value, provenance=list(merged.values()))
    state.update(revision=state["revision"] + 1, attempts=state["attempts"] + 1)
    state["seen_hashes"].append(digest)
    state.pop("review_binding", None)
    context = _save(out, context, state)
    write_json(out / f".work/history/revision-{state['revision']:02d}.json",
               {"metadata": value, "provenance": context["provenance"], "agent": agent or {},
                "model_identity_verified": False, "at": now()})
    return {"ok": True, "revision": state["revision"], "input_hash": context["input_hash"],
            "metadata_hash": digest, "checks": checks,
            "message": "Accepted as working metadata only; the AI chooses whether to review, revise or deliver."}


def record_metadata(out, candidate):
    out, state, context, result = _candidate(out, candidate)
    if context["intent"] == "review":
        raise WorkflowError("Review-only runs preserve the original; record suggestions in the review")
    value = result.get("metadata")
    if not isinstance(value, dict):
        raise WorkflowError("Candidate requires a metadata object")
    _guard_structure(value, context["structure"])
    provenance = _semantic_provenance(value, context["metadata"], result.get("provenance", []), context)
    return _accept_metadata(out, state, context, value, provenance, result.get("agent"))


def record_review(out, candidate, *, independent=False):
    out, state, context, result = _candidate(out, candidate)
    if context["intent"] == "generate-review" and not independent:
        raise WorkflowError("A combined task requires a fresh independent Reviewer; the flag attests host isolation")
    entries = _check_review(context, result)
    patches = [{"op": "replace", "pointer": e["pointer"], "old_value": get_pointer(context["metadata"], e["pointer"]),
                "value": e["proposed_value"], "evidence_ids": e["evidence_ids"], "reason": e["comment"]}
               for e in entries if "proposed_value" in e]
    suggested = copy.deepcopy(context["metadata"])
    for patch in patches:
        if patch["old_value"] == patch["value"]:
            raise WorkflowError("Suggested replacement is identical to the current value")
        set_pointer(suggested, patch["pointer"], patch["value"])
    checks = _validation(suggested, context, out)
    review = {"input_hash": context["input_hash"], "metadata_hash": context["metadata_hash"],
              "evidence_hash": json_hash(context["evidence"]), "entries": entries,
              "summary": result.get("summary", ""), "agent": result.get("agent", {}),
              "independent_context": bool(independent), "decision_counts": review_decision_counts(entries),
              "checks": _validation(context["metadata"], context, out)}
    review["agent_decision_counts"] = review_decision_counts([e for e in entries if e.get("origin") != "program"])
    review["program_decision_counts"] = review_decision_counts([e for e in entries if e.get("origin") == "program"])
    write_json(out / ".work/review.json", review)
    state["review_binding"] = {"metadata_hash": review["metadata_hash"], "evidence_hash": review["evidence_hash"],
                               "review_hash": json_hash(review), "independent": bool(independent)}
    write_json(out / ".work/state.json", state)
    return {"ok": True, "metadata_hash": context["metadata_hash"], "decision_counts": review["decision_counts"],
            "agent_decision_counts": review["agent_decision_counts"],
            "program_decision_counts": review["program_decision_counts"], "suggested_checks": checks,
            "message": "Opinions recorded only. The AI chooses which issue to address or whether to deliver a review."}


def _current_review(out, state, context):
    binding = state.get("review_binding")
    if not binding:
        return None
    review = load_json(out / ".work/review.json")
    if (binding["metadata_hash"] != context["metadata_hash"] or binding["evidence_hash"] != json_hash(context["evidence"])
            or binding["review_hash"] != json_hash(review)):
        raise WorkflowError("Review is stale or changed; request a fresh review")
    return review


def apply_patch(out, candidate):
    out, state, context, result = _candidate(out, candidate)
    if context["intent"] == "review":
        raise WorkflowError("Review-only runs preserve the original; export suggestions with deliver")
    review = _current_review(out, state, context)
    if review is None or result.get("base_hash") != context["metadata_hash"]:
        raise WorkflowError("A patch requires a current review and matching base_hash")
    allowed = [e["pointer"] for e in review["entries"] if e["decision"] in {"conflict", "unknown"}]
    patches = result.get("patches")
    if not isinstance(patches, list) or not patches:
        raise WorkflowError("Patch requires nonempty patches")
    value = copy.deepcopy(context["metadata"])
    provenance, changed = [], []
    for patch in patches:
        pointer = patch.get("pointer")
        if not isinstance(pointer, str) or not any(pointer == p or pointer.startswith(p + "/") for p in allowed):
            raise WorkflowError("Patch is outside reviewed issue scope")
        if any(pointer == p or pointer.startswith(p + "/") or p.startswith(pointer + "/") for p in changed):
            raise WorkflowError("Overlapping patches are not supported")
        changed.append(pointer)
        _check_evidence(patch.get("evidence_ids", []), context, required=True)
        if not patch.get("reason") or patch.get("op") != "replace" or get_pointer(value, pointer) != patch.get("old_value") or "value" not in patch:
            raise WorkflowError("Patch requires replace, matching old_value, new value, evidence and reason")
        set_pointer(value, pointer, patch["value"])
        for leaf, item in leaves(patch["value"], pointer):
            provenance.append({"pointer": leaf, "status": "unknown" if empty(item) or item == "ToDo" else "supported",
                               "evidence_ids": patch["evidence_ids"], "rationale": patch["reason"]})
    _guard_structure(value, context["structure"])
    provenance = _semantic_provenance(value, context["metadata"], provenance, context)
    return _accept_metadata(out, state, context, value, provenance, result.get("agent"))


def add_evidence(out, source, *, kind="source", source_url=None):
    if kind not in {"source", "background", "document", "declaration"}:
        raise WorkflowError("Unsupported supplementary evidence kind")
    out, state, context = _load(out, writable=True)
    source = Path(source)
    if source.stat().st_size > 2 * 1024 * 1024:
        raise WorkflowError("Evidence text is limited to 2 MiB")
    content = source.read_text(encoding="utf-8-sig")
    digest = file_hash(source)
    origin = source_url or "supplementary/" + digest
    eid = "ev-" + json_hash({"kind": kind, "content": content, "source": origin})[:16]
    if eid in _known_ids(context):
        raise WorkflowError("Evidence is already registered")
    target = out / ".work/inputs" / (eid + ".txt")
    shutil.copyfile(source, target)
    context["snapshots"].append({"kind": kind, "path": target.relative_to(out).as_posix(), "sha256": file_hash(target)})
    context["evidence"].append({"id": eid, "kind": kind, "source": origin, "content": content})
    state.pop("review_binding", None)
    context = _save(out, context, state)
    return {"ok": True, "evidence_id": eid, "input_hash": context["input_hash"],
            "message": "Evidence added. Earlier candidates and reviews are stale; the AI chooses the next action."}


def _summary(value):
    value = load_json(value) if isinstance(value, (str, Path)) else copy.deepcopy(value)
    if not isinstance(value, dict) or not isinstance(value.get("overview"), str) or not value["overview"].strip():
        raise WorkflowError("Summary needs a short overview")
    if len(value["overview"]) > 1500:
        raise WorkflowError("Condense the summary overview to at most 1500 characters")
    for key in ("needs_attention", "notes"):
        items = value.get(key, [])
        if not isinstance(items, list) or len(items) > 8 or any(not isinstance(i, str) or not i.strip() or len(i) > 600 for i in items):
            raise WorkflowError("Summary lists must contain at most eight concise text items; combine related facts")
        value[key] = items
    return value


def deliver(out, summary):
    out, state, context = _load(out, writable=True)
    summary = _summary(summary)
    review = _current_review(out, state, context)
    checks = _validation(context["metadata"], context, out)
    if context["intent"] != "review":
        if state["revision"] == 0:
            return {"ok": False, "error": "no_accepted_metadata"}
        if not checks.get("mechanical_valid", False):
            return {"ok": False, "checks": checks, "message": "Successful metadata delivery requires passing checks."}
        if context["intent"] == "generate-review":
            if not review or not review["independent_context"]:
                return {"ok": False, "error": "current_independent_review_required"}
            if review["decision_counts"]["conflict"]:
                return {"ok": False, "error": "unresolved_conflicts", "counts": review["decision_counts"]}
    elif not review:
        return {"ok": False, "error": "current_review_required"}
    outputs = []
    if context["intent"] != "review":
        write_json(out / "metadata.json", context["metadata"])
        outputs.append("metadata.json")
    if review:
        _write_text(out / "review.md", render_review_report(review))
        outputs.append("review.md")
        patches = [{"pointer": e["pointer"], "value": e["proposed_value"]}
                   for e in review["entries"] if "proposed_value" in e]
        if context["intent"] == "review" and patches:
            suggested = copy.deepcopy(context["metadata"])
            for patch in patches:
                set_pointer(suggested, patch["pointer"], patch["value"])
            suggestion_checks = _validation(suggested, context, out)
            if suggestion_checks.get("mechanical_valid", False):
                write_json(out / "metadata.suggested.json", suggested)
                outputs.append("metadata.suggested.json")
            else:
                summary["notes"].append("Suggested metadata was not exported because it did not pass program checks; inspect the tool result before revising.")
    lines = ["# Result", "", _text(summary["overview"]), "", "Program validation: " + ("passed" if checks.get("mechanical_valid") else "errors reported in the review"),
             "", "## Needs attention", ""]
    lines += ["- " + _text(item) for item in summary["needs_attention"]] or ["None reported by the agent."]
    lines += ["", "## Notes", ""]
    lines += ["- " + _text(item) for item in summary["notes"]] or ["None."]
    if review:
        counts = review["decision_counts"]
        lines += ["", f"Review: {counts['conflict']} conflicts; {counts['unknown']} unresolved field decisions. See review.md."]
    else:
        lines += ["", "No independent semantic review was performed."]
    warnings = sum(i.get("severity") == "warning" for i in checks.get("issues", []))
    lines += ["", f"Program warnings: {warnings}. Mechanical validity does not prove factual correctness."]
    _write_text(out / "summary.md", "\n".join(lines) + "\n")
    outputs.append("summary.md")
    outcome = "delivered_with_notes" if summary["needs_attention"] or warnings or (review and (review["decision_counts"]["unknown"] or review["decision_counts"]["conflict"])) else "delivered"
    state.update(status="delivered", outcome=outcome, outputs=outputs, delivered_hash=context["metadata_hash"], updated_at=now())
    write_json(out / ".work/state.json", state)
    return {"ok": True, "outputs": outputs, "checks": checks,
            "status": outcome}


def stop(out, summary):
    out, state, context = _load(out, writable=True)
    summary = _summary(summary)
    lines = ["# Task stopped", "", _text(summary["overview"]), "", "No successful metadata delivery was produced.", "", "## Needs attention", ""]
    lines += ["- " + _text(item) for item in summary["needs_attention"]] or ["The agent could not complete the task within its available evidence or budget."]
    lines += ["", "## Notes", ""] + ["- " + _text(item) for item in summary["notes"]]
    _write_text(out / "summary.md", "\n".join(lines) + "\n")
    state.update(status="stopped", updated_at=now())
    write_json(out / ".work/state.json", state)
    return {"ok": True, "status": "stopped", "outputs": ["summary.md"]}
