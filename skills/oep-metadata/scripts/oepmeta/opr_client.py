"""Conservative adapter for OEP's existing reviewer page JSON POST protocol.

Only authenticated session cookies + CSRF, save and submit are supported.
Protocol/layout checks are intentionally strict; deployed compatibility still
needs an authorized test account. This is not a general comment API.
"""

import copy
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

from .common import WorkflowError, now, load_json, write_json, json_hash, leaves, parts, empty
from .oep_client import plan_directory, OEPClient, Page, table_name, check_plan, save_plan, claim_attempt


def _script_json(html, name):
    pattern = r"(?:var\s+|window\.)?" + re.escape(name) + r'\s*=\s*JSON\.parse\(\s*("(?:\\.|[^"\\])*")\s*\)'
    match = re.search(pattern, html)
    if match is None:
        raise WorkflowError("Unsupported OPR page layout: missing structured page state")
    try:
        return json.loads(json.loads(match.group(1)))
    except (ValueError, TypeError):
        raise WorkflowError("Malformed structured OPR page state") from None


def parse_review_page(html):
    page = Page(html)
    if not any(a.get("id") == "opr-page-marker" and a.get("data-opr-page") == "reviewer" for _, a in page.nodes):
        raise WorkflowError("Expected authenticated OPR reviewer page; check supplied session")
    config = _script_json(html, "config")
    state = _script_json(html, "state_dict")
    history = _script_json(html, "field_history")
    if not isinstance(config, dict) or not isinstance(history, dict) or state is not None and not isinstance(state, dict):
        raise WorkflowError("Unsupported OPR state format")
    required = ("table", "url_peer_review", "url_table", "review_id", "read_only", "review_finished", "topic")
    if any(k not in config for k in required):
        raise WorkflowError("Unsupported OPR configuration")
    # Persist only the known public configuration, never future login/CSRF
    # additions a deployment might include in its page configuration.
    config = {key: config[key] for key in required}
    if not isinstance(config["read_only"], bool):
        raise WorkflowError("Unverified OPR turn state")
    fields = {}
    for _, attrs in page.nodes:
        if "field" not in attrs.get("class", "").split():
            continue
        key, category = attrs.get("data-fieldkey"), attrs.get("data-category")
        if not key or category not in ("general", "spatial", "temporal", "source", "license") or key in fields:
            raise WorkflowError("Ambiguous or unsupported OPR field mapping")
        fields[key] = {"category": category, "value": attrs.get("data-fieldvalue", "")}
    if not fields:
        raise WorkflowError("OPR page exposes no reviewable fields")
    if any(key not in fields or not isinstance(value, list) or any(not isinstance(x, dict) for x in value)
           for key, value in history.items()):
        raise WorkflowError("Unsupported OPR field history")
    return {"config": config, "fields": fields, "state": state or {}, "history": history}


def _effective_empty(key, value):
    return empty(value) or key in {f"extent.boundingBox.{i}" for i in range(4)} and str(value).strip() == "0"


def _mapped_fields(metadata):
    if not isinstance(metadata, dict) or not isinstance(metadata.get("resources"), list) or len(metadata["resources"]) != 1:
        raise WorkflowError("OPR adapter requires one resource; page protocol loses resource indices")
    fields = {}
    for pointer, value in leaves(metadata):
        tokens = parts(pointer)
        if len(tokens) < 3 or tokens[:2] != ["resources", "0"] or isinstance(value, dict):
            continue
        tokens = tokens[2:]
        if any("." in token for token in tokens):
            raise WorkflowError("OPR dotted field keys cannot express this metadata key")
        root = tokens[0]
        category = {"spatial": "spatial", "temporal": "temporal", "sources": "source", "licenses": "license"}.get(root, "general")
        key = ".".join(tokens[1:] if root in ("spatial", "temporal") else tokens)
        if key in fields:
            raise WorkflowError("OPR field keys collide after resource/category prefix removal")
        fields[key] = {"pointer": pointer, "category": category, "value": str(value), "raw_value": value}
    return fields


def _assert_snapshot(metadata, page):
    mapped = _mapped_fields(metadata)
    visible = {key: {"category": item["category"], "value": item["value"]} for key, item in mapped.items()}
    if visible != page["fields"]:
        raise WorkflowError("Metadata differs from the OPR frozen resource snapshot; prepare against that snapshot")
    return mapped


def _review_fingerprint(page):
    config = page["config"]
    return json_hash({"fields": page["fields"], "state": page["state"], "history": page["history"],
                      "table": config["table"], "review_id": config["review_id"],
                      "read_only": config["read_only"], "review_finished": config["review_finished"]})


def build_review_payload(metadata, entries, page, *, action="save", timestamp=None):
    if action not in ("save", "submit"):
        raise WorkflowError("Only OPR save and submit are supported")
    mapped = _assert_snapshot(metadata, page)
    pointers = {item["pointer"]: (key, item) for key, item in mapped.items()}
    if not isinstance(entries, list):
        raise WorkflowError("Expected finalized review entries")
    history = copy.deepcopy(page["history"])
    updates = {}
    skipped = []
    seen = set()
    stamp = int(time.time() * 1000) if timestamp is None else timestamp
    for entry in entries:
        if not isinstance(entry, dict):
            raise WorkflowError("Malformed finalized review entry")
        pointer = entry.get("pointer")
        if not isinstance(pointer, str) or pointer in seen:
            raise WorkflowError("Missing or duplicate finalized review pointer")
        seen.add(pointer)
        decision = entry.get("decision")
        if decision not in ("supported", "conflict", "unknown", "not_applicable"):
            raise WorkflowError("Invalid review decision")
        if pointer not in pointers:
            if decision == "conflict" or "proposed_value" in entry:
                raise WorkflowError("Review contains a structural/top-level edit the OPR page cannot express")
            skipped.append({"pointer": pointer, "reason": "outside_opr_resource_fields"})
            continue
        key, item = pointers[pointer]
        if _effective_empty(key, item["value"]):
            if "proposed_value" in entry or decision == "conflict":
                raise WorkflowError("OPR cannot propose edits to empty/disabled fields; use metadata-upload")
            skipped.append({"pointer": pointer, "reason": "empty_disabled_opr_field"})
            continue
        if decision in ("unknown", "not_applicable"):
            if action == "submit":
                raise WorkflowError("Unresolved review decisions block OPR submit; save a partial draft instead")
            skipped.append({"pointer": pointer, "reason": decision})
            continue
        comment = entry.get("comment", "")
        if not isinstance(comment, str) or not comment.strip() or not isinstance(entry.get("evidence_ids"), list) or not entry["evidence_ids"]:
            raise WorkflowError("Review needs a comment and evidence references before upload")
        proposed = entry.get("proposed_value", "")
        if decision == "supported" and "proposed_value" in entry:
            raise WorkflowError("Accepted review field must not carry a replacement")
        if "proposed_value" in entry and (not isinstance(proposed, str) or not proposed.strip() or not isinstance(item["raw_value"], str)):
            raise WorkflowError("OPR text suggestions cannot represent this typed or empty edit")
        state = "ok" if decision == "supported" else "suggestion" if "proposed_value" in entry else "rejected"
        contribution = {"timestamp": stamp, "user": "oep_reviewer", "role": "reviewer",
                        "contributorValue": item["value"], "newValue": proposed,
                        "comment": comment if state == "suggestion" else "",
                        "additionalComment": comment if state == "rejected" else "",
                        "reviewerSuggestion": proposed, "state": state}
        history.setdefault(key, []).append(contribution)
        updates[key] = contribution
    if not updates:
        raise WorkflowError("No platform-expressible review opinions to upload")
    required = {key for key, item in mapped.items() if not _effective_empty(key, item["value"])}
    # Submission requires a fresh explicit decision for every filled platform field.
    # An old Accept never fills a hole left unknown in this review run.
    if action == "submit" and required - updates.keys():
        raise WorkflowError("Incomplete field coverage blocks OPR submit")
    if action == "submit" and all(item["state"] == "ok" for item in updates.values()):
        raise WorkflowError("All fields accepted: OEP requires its explicit finish/badge workflow; use save")
    reviews = [{"category": mapped[key]["category"], "key": key, "fieldReview": values}
               for key, values in history.items() if values]
    config = page["config"]
    model = {"topic": config["topic"], "table": config["table"], "dateStarted": None, "dateFinished": None,
             # Mirrors the existing frontend envelope (not the input's OEMetadata version).
             "metadataVersion": "v1.6.0", "reviews": reviews, "reviewFinished": False, "grantedBadge": None,
             "metaMetadata": {"reviewVersion": "OEP-0.1.0", "metadataLicense": {
                 "name": "CC0-1.0", "title": "Creative Commons Zero v1.0 Universal",
                 "path": "https://creativecommons.org/publicdomain/zero/1.0/"}}}
    return {"reviewType": action, "reviewData": model}, skipped, updates


class OPRClient(OEPClient):
    def _check_session(self):
        if not any(cookie.name == "sessionid" for cookie in self.session.cookies):
            raise WorkflowError("Review upload requires an explicit authenticated session or Netscape cookie file; API Token is not a web login")

    def _review_path(self, table, review_id):
        table = table_name(table)
        if review_id is not None and (isinstance(review_id, bool) or not str(review_id).isdigit() or int(review_id) < 1):
            raise WorkflowError("Expected a positive OPR review ID")
        return f"/database/{table}/open_peer_review/" + (f"{int(review_id)}/" if review_id is not None else "")

    def _role_gate(self, table, path):
        self._check_session()
        html = self._request("GET", f"/database/{table_name(table)}").text
        page = Page(html)
        allowed = []
        for _, attrs in page.nodes:
            if attrs.get("id") in ("opr-button-start", "opr-button-reviewer-continue"):
                if "disabled" not in attrs.get("class", "").split() and "disabled" not in attrs:
                    allowed.append(attrs.get("data-url"))
        if path not in allowed:
            raise WorkflowError("OPR role/turn unverified: account may be contributor, another reviewer, or waiting for the other party")
        # These buttons are rendered by server-side authenticated account checks,
        # excluding contributor=self. Never infer identity from an AI subagent.

    def _read_review(self, table, path, review_id, *, editable=True):
        page = parse_review_page(self._request("GET", path).text)
        config = page["config"]
        if (config["table"] != table or config["url_peer_review"] != path or
                str(config["review_id"]) != str(int(review_id) if review_id is not None else None) or
                config["url_table"] != f"/database/{table}"):
            raise WorkflowError("OPR page targets a different table or review")
        if editable and (config["read_only"] or config["review_finished"]):
            raise WorkflowError("OPR is finished or it is not the reviewer's turn")
        return page

    def prepare_review_upload(self, metadata, entries, table, out_dir, *, action="save", review_id=None):
        if action == "submit" and review_id is None:
            raise WorkflowError("Save a new OPR draft first to obtain its review ID, then prepare submit")
        metadata = load_json(metadata) if isinstance(metadata, (str, Path)) else copy.deepcopy(metadata)
        table = table_name(table)
        path = self._review_path(table, review_id)
        self._role_gate(table, path)
        page = self._read_review(table, path, review_id)
        payload, skipped, updates = build_review_payload(metadata, entries, page, action=action)
        out = Path(out_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        # Parsed snapshots contain no raw HTML, headers, cookies, or CSRF tokens.
        write_json(out / "opr.remote.backup.json", page)
        write_json(out / "opr.upload.json", payload)
        return save_plan(out, {"operation": "review-upload", "created_at": now(), "base_url": self.base_url,
                               "table": table, "review_id": review_id, "path": path, "action": action,
                               "metadata_hash": json_hash(metadata), "entries_hash": json_hash(entries),
                               "remote_hash": _review_fingerprint(page), "payload_hash": json_hash(payload),
                               "out_dir": ".", "updates": updates, "skipped": skipped,
                               "limitations": ["Source-derived web protocol; live deployment unverified",
                                               "Frozen snapshot verified against platform-exposed resource fields only",
                                               "Client recheck is not atomic conditional-write protection"]})

    def _csrf(self):
        cookies = self.session.cookies.get_dict(domain=urlsplit(self.base_url).hostname)
        # requests uses leading-dot domains for some explicitly imported jars.
        if not cookies.get("csrftoken"):
            cookies = {c.name: c.value for c in self.session.cookies if c.domain.lstrip(".") == urlsplit(self.base_url).hostname}
        token = cookies.get("csrftoken")
        if not token or "\n" in token or "\r" in token:
            raise WorkflowError("Authenticated OEP session has no usable CSRF cookie")
        return token

    def execute_review_upload(self, plan, metadata, entries, *, execute=False, expected_plan_hash=None):
        plan = check_plan(plan, "review-upload", expected_plan_hash)
        metadata = load_json(metadata) if isinstance(metadata, (str, Path)) else copy.deepcopy(metadata)
        if (plan["base_url"] != self.base_url or json_hash(metadata) != plan["metadata_hash"] or
                json_hash(entries) != plan["entries_hash"]):
            raise WorkflowError("Review target or local inputs changed; prepare a new plan")
        out = plan_directory(plan)
        payload = load_json(out / "opr.upload.json")
        if json_hash(payload) != plan["payload_hash"] or payload.get("reviewType") != plan["action"]:
            raise WorkflowError("Prepared review payload changed")
        if not execute:
            return {"status": "dry_run", "plan_hash": plan["plan_hash"]}
        if (out / "upload.attempt.json").exists():
            raise WorkflowError("This plan already attempted a write; inspect review before preparing another plan")
        self._role_gate(plan["table"], plan["path"])
        current = self._read_review(plan["table"], plan["path"], plan["review_id"])
        _assert_snapshot(metadata, current)
        if _review_fingerprint(current) != plan["remote_hash"]:
            raise WorkflowError("Remote OPR snapshot, turn, or field history changed; prepare a new plan")
        token = self._csrf()
        claim_attempt(out, plan["plan_hash"])
        try:
            response = self._request("POST", plan["path"], json=payload,
                                     headers={"X-CSRFToken": token, "Referer": self._url(plan["path"]), "Origin": self.base_url})
            result = self._json(response, write=True)
            if result != {"status": "success"}:
                raise WorkflowError("Write outcome uncertain; unexpected OPR response; do not retry blindly")
            review_id = plan["review_id"]
            if review_id is None:
                # The existing POST only returns status, not ID. Discover the
                # new server-rendered continue button; never guess an ID.
                table_page = Page(self._request("GET", f"/database/{plan['table']}").text)
                paths = [a.get("data-url", "") for _, a in table_page.nodes
                         if a.get("id") in ("opr-button-reviewer-continue", "opr-button-contributor-continue")]
                regex = re.compile(re.escape(f"/database/{plan['table']}/") + r"(?:open_peer_review|opr_contributor)/(\d+)/$")
                ids = {int(m.group(1)) for path in paths if (m := regex.fullmatch(path))}
                if len(ids) != 1:
                    raise WorkflowError("Write acknowledged; new review ID cannot be verified; do not retry")
                review_id = ids.pop()
            readback_path = self._review_path(plan["table"], review_id)
            readback = self._read_review(plan["table"], readback_path, review_id, editable=False)
            _assert_snapshot(metadata, readback)
            write_json(out / "opr.readback.json", readback)
            for key, expected in plan["updates"].items():
                contributions = readback["history"].get(key, [])
                if expected not in contributions or readback["state"].get(key) != expected["state"]:
                    raise WorkflowError("Write acknowledged but field opinions did not match readback; do not retry")
            if plan["action"] == "submit" and not readback["config"]["read_only"]:
                raise WorkflowError("Submission turn transition was not confirmed; do not retry")
            if plan["action"] == "save" and readback["config"]["read_only"]:
                raise WorkflowError("Draft turn unexpectedly changed; do not retry")
            receipt = {"operation": "review-upload", "status": "verified", "action": plan["action"],
                       "completed_at": now(), "plan_hash": plan["plan_hash"], "review_id": review_id,
                       "url": self._url(readback_path), "limitations": plan["limitations"]}
            write_json(out / "upload.receipt.json", receipt)
            return receipt
        except WorkflowError:
            write_json(out / "upload.receipt.json", {"operation": "review-upload", "status": "not_verified_do_not_retry", "plan_hash": plan["plan_hash"], "at": now()})
            raise
