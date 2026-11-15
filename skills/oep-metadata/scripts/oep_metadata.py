#!/usr/bin/env python3
"""CLI for five OEP metadata operations and supporting deterministic tools."""

import argparse
import json
import sys
import time
from pathlib import Path

from oepmeta.common import WorkflowError, load_json, now


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--pretty", action="store_true", help="Indent JSON for manual inspection")
    commands = root.add_subparsers(dest="command", required=True)
    p = commands.add_parser("collect")
    p.add_argument("--intent", required=True, choices=("generate", "review", "generate-review"))
    p.add_argument("--out", required=True)
    p.add_argument("--data")
    p.add_argument("--metadata")
    p.add_argument("--table")
    p.add_argument("--background", action="append", default=[])
    p.add_argument("--base-url", default="https://openenergyplatform.org")
    p.add_argument("--max-rows", type=int)
    p.add_argument("--ontology-index")
    p.add_argument("--max-changes", type=int, default=8)
    p.add_argument("--view", choices=("auto", "generation", "reviewer", "full"), default="auto")
    p = commands.add_parser("inspect")
    p.add_argument("--out", required=True)
    p.add_argument("--view", choices=("auto", "generation", "reviewer", "status", "full"), default="auto")
    p = commands.add_parser("review-input")
    p.add_argument("--out", required=True)
    for name in ("record-metadata", "record-review", "apply-patch"):
        p = commands.add_parser(name)
        p.add_argument("--out", required=True)
        p.add_argument("--candidate", required=True)
        if name == "record-review":
            p.add_argument("--independent", action="store_true", help="Attest a fresh independent agent context")
    for name in ("deliver", "stop"):
        p = commands.add_parser(name)
        p.add_argument("--out", required=True)
        p.add_argument("--summary", required=True)
    p = commands.add_parser("evidence-add")
    p.add_argument("--out", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--kind", choices=("source", "background", "document", "declaration"), default="source")
    p.add_argument("--source-url")
    p = commands.add_parser("check", aliases=["validate"])
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--metadata", help="Bare metadata document; candidate envelopes are also recognized")
    source.add_argument("--candidate", help="Candidate envelope containing a metadata object")
    p.add_argument("--run", help="Use this run's frozen evidence for checks")
    p.add_argument("--profile")
    p.add_argument("--db-schema")
    p.add_argument("--ontology-index")
    p = commands.add_parser("profile")
    p.add_argument("--data", required=True)
    p.add_argument("--max-rows", type=int)
    p = commands.add_parser("template")
    p.add_argument("--profile", required=True)
    p.add_argument("--name")
    p = commands.add_parser("schema")
    p.add_argument("--pointer", required=True, help="Metadata instance pointer, e.g. /resources/0/licenses")
    p = commands.add_parser("ontology-index")
    p.add_argument("--source", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--out", required=True)
    p = commands.add_parser("ontology-search")
    p.add_argument("--index", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=10)
    for name in ("metadata-upload", "review-upload"):
        p = commands.add_parser(name)
        p.add_argument("--metadata", required=True)
        p.add_argument("--table", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--base-url", default="https://openenergyplatform.org")
        p.add_argument("--execute", action="store_true")
        p.add_argument("--plan")
        p.add_argument("--plan-hash", help="Expected plan hash displayed during preparation")
        if name == "metadata-upload":
            p.add_argument("--token-env", default="OEP_API_TOKEN")
        else:
            p.add_argument("--review", required=True)
            p.add_argument("--action", choices=("save", "submit"), default="save")
            p.add_argument("--review-id", type=int)
            p.add_argument("--cookies", help="Explicit Netscape-format cookie file for an authorized OEP web session")
    return root


def _trace(args, started, code, output):
    directory = getattr(args, "out", None) or getattr(args, "run", None)
    if not directory or not (Path(directory) / ".work/state.json").is_file():
        return
    try:
        state = load_json(Path(directory) / ".work/state.json")
        event = {"at": now(), "command": args.command, "exit_code": code,
                 "dispatch_elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                 "response_bytes": len((output + "\n").encode("utf-8")),
                 "revision": state.get("revision"), "input_hash": state.get("input_hash")}
        with (Path(directory) / ".work/tool-events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event) + "\n")
    except (OSError, ValueError, TypeError):
        # Diagnostic logging must not change a tool's business outcome.
        pass


def main(argv=None):
    args = parser().parse_args(argv)
    started = time.perf_counter()
    try:
        result = dispatch(args)
        output = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None,
                            separators=None if args.pretty else (",", ":"), allow_nan=False)
        code = 0 if result.get("ok", True) else 1
        _trace(args, started, code, output)
        print(output)
        return code
    except (WorkflowError, ValueError, OSError, KeyError, TypeError) as error:
        # Network adapters sanitize their own errors; credentials never enter CLI args.
        output = json.dumps({"error": str(error), "type": type(error).__name__}, ensure_ascii=False)
        _trace(args, started, 2, output)
        print(output, file=sys.stderr)
        return 2


def dispatch(args):
    from oepmeta import workflows
    command = args.command
    if command == "collect":
        return workflows.collect(args.intent, args.out, data=args.data, metadata=args.metadata, table=args.table,
                                 background=args.background, base_url=args.base_url, max_rows=args.max_rows,
                                 max_changes=args.max_changes, ontology_index=args.ontology_index, view=args.view)
    if command == "inspect":
        return workflows.inspect(args.out, view=args.view)
    if command == "review-input":
        return workflows.reviewer_input(args.out)
    if command == "record-metadata":
        return workflows.record_metadata(args.out, args.candidate)
    if command == "record-review":
        return workflows.record_review(args.out, args.candidate, independent=args.independent)
    if command == "apply-patch":
        return workflows.apply_patch(args.out, args.candidate)
    if command in {"deliver", "stop"}:
        return getattr(workflows, command)(args.out, args.summary)
    if command == "evidence-add":
        return workflows.add_evidence(args.out, args.file, kind=args.kind, source_url=args.source_url)
    if command in {"check", "validate"}:
        if args.run and (args.profile or args.db_schema or args.ontology_index):
            raise WorkflowError("Use --run or explicit evidence options, not both")
        return workflows.check(args.candidate or args.metadata, out=args.run, candidate=bool(args.candidate),
                               profile=load_json(args.profile) if args.profile else None,
                               db_schema=load_json(args.db_schema) if args.db_schema else None,
                               ontology_index=args.ontology_index)
    if command == "profile":
        from oepmeta.profile import profile_data
        return {"ok": True, "profile": profile_data(args.data, max_rows=args.max_rows)}
    if command == "template":
        from oepmeta.validate import build_skeleton
        return {"ok": True, "metadata": build_skeleton(load_json(args.profile), args.name)}
    if command == "schema":
        from oepmeta.validate import schema_fragment
        return schema_fragment(args.pointer)
    if command == "ontology-index":
        from oepmeta.ontology import build_index
        return build_index(args.source, args.out, args.version)
    if command == "ontology-search":
        from oepmeta.ontology import search
        return search(args.index, args.query, args.limit)
    if command == "metadata-upload":
        from oepmeta.oep_client import OEPClient, check_plan, plan_directory
        from oepmeta.validate import validate_metadata
        metadata = load_json(args.metadata)
        validation = validate_metadata(metadata)
        if not validation["schema_valid"] or any(i.get("severity") == "error" for i in validation.get("issues", [])):
            raise WorkflowError("Metadata upload requires resolving validation errors; inspect the validate command output")
        client = OEPClient(base_url=args.base_url)
        if not args.execute:
            return client.prepare_metadata_upload(metadata, args.table, args.out)
        if not args.plan:
            raise WorkflowError("--execute requires the reviewed --plan file")
        plan = check_plan(args.plan, "metadata-upload", args.plan_hash)
        if plan.get("table") != args.table or plan_directory(plan) != Path(args.out).resolve():
            raise WorkflowError("Command target/output does not match the selected upload plan")
        return client.execute_metadata_upload(plan, metadata, execute=True, token_env=args.token_env, expected_plan_hash=args.plan_hash)
    if command == "review-upload":
        from oepmeta.opr_client import OPRClient
        from oepmeta.oep_client import load_cookie_session, check_plan, plan_directory
        metadata = load_json(args.metadata)
        review = load_json(args.review)
        from oepmeta.common import json_hash
        if review.get("metadata_hash") != json_hash(metadata):
            raise WorkflowError("Review is not bound to the selected metadata")
        entries = review.get("entries")
        if not isinstance(entries, list):
            raise WorkflowError("A finalized review JSON with entries is required")
        session = load_cookie_session(args.cookies, args.base_url) if args.cookies else None
        client = OPRClient(base_url=args.base_url, session=session)
        if not args.execute:
            return client.prepare_review_upload(metadata, entries, args.table, args.out, action=args.action, review_id=args.review_id)
        if not args.plan:
            raise WorkflowError("--execute requires the reviewed --plan file")
        plan = check_plan(args.plan, "review-upload", args.plan_hash)
        if (plan.get("table") != args.table or plan.get("action") != args.action or
                plan.get("review_id") != args.review_id or plan_directory(plan) != Path(args.out).resolve()):
            raise WorkflowError("Command target/action/output does not match the selected upload plan")
        return client.execute_review_upload(plan, metadata, entries, execute=True, expected_plan_hash=args.plan_hash)
    raise WorkflowError("Unknown command")


if __name__ == "__main__":
    sys.exit(main())
