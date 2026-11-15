"""Protocol/guard tests only: HTTP is injected; nothing writes to a live OEP."""

import copy
import json
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/oep-metadata/scripts"))

from oepmeta.common import WorkflowError, json_hash
from oepmeta.oep_client import OEPClient, safe_base_url
from oepmeta.opr_client import OPRClient, build_review_payload, parse_review_page

BASE = "https://openenergyplatform.org"
META_PATH = "/api/v0/tables/example/meta/"
TABLE_PATH = "/database/example"
REVIEW_PATH = "/database/example/open_peer_review/7/"
METADATA = {"resources": [{"title": "Wrong", "spatial": {"extent": {"name": "Germany"}},
                           "licenses": [{"name": "CC-BY-4.0"}]}]}
ENTRIES = [
    {"pointer": "/resources/0/title", "decision": "conflict", "comment": "Source says Correct", "evidence_ids": ["source:1"], "proposed_value": "Correct"},
    {"pointer": "/resources/0/spatial/extent/name", "decision": "supported", "comment": "Source identifies Germany", "evidence_ids": ["source:1"]},
    {"pointer": "/resources/0/licenses/0/name", "decision": "supported", "comment": "Explicit license declaration", "evidence_ids": ["source:2"]},
]


def response(value, status=200, *, text=False):
    result = requests.Response()
    result.status_code = status
    result.encoding = "utf-8"
    result._content = (value if text else json.dumps(value)).encode()
    return result


class FakeSession(requests.Session):
    def __init__(self, steps=(), authenticated=False):
        super().__init__()
        self.steps = list(steps)
        self.calls = []
        if authenticated:
            self.cookies.set("sessionid", "SECRET-SESSION", domain="openenergyplatform.org", secure=True)
            self.cookies.set("csrftoken", "SECRET-CSRF", domain="openenergyplatform.org", secure=True)

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        assert kwargs["allow_redirects"] is False
        assert self.steps, f"Unexpected request {method} {url}"
        expected_method, path, result = self.steps.pop(0)
        assert method == expected_method
        assert url == BASE + path
        if isinstance(result, BaseException):
            raise result
        return result


def role_table(*, allowed=True, new=False):
    if not allowed:
        return '<button id="opr-button-contributor-continue" data-url="/database/example/opr_contributor/7/"></button>'
    return f'<button id="{"opr-button-start" if new else "opr-button-reviewer-continue"}" data-url="{"/database/example/open_peer_review/" if new else REVIEW_PATH}"></button>'


def opr_page(*, read_only=False, finished=False, history=None, state=None, title="Wrong", review_id=7):
    config = {"table": "example", "url_peer_review": f"/database/example/open_peer_review/{review_id}/" if review_id else "/database/example/open_peer_review/",
              "url_table": TABLE_PATH, "review_id": review_id, "read_only": read_only,
              "review_finished": finished, "topic": ["model_draft"], "can_add": False}
    fields = [("title", "general", title), ("extent.name", "spatial", "Germany"), ("licenses.0.name", "license", "CC-BY-4.0")]
    rows = "".join(f'<div class="field review__item" data-fieldkey="{key}" data-fieldvalue="{value}" data-category="{category}"></div>' for key, category, value in fields)
    scripts = "".join(f'{name} = JSON.parse({json.dumps(json.dumps(value))});' for name, value in
                      [("var config", config), ("window.state_dict", state or {}), ("window.field_history", history or {})])
    return f'<div id="opr-page-marker" data-opr-page="reviewer"></div>{rows}<script>{scripts}</script>'


def metadata_plan(tmp_path, *, public_page="<p>Not reviewed</p>"):
    session = FakeSession([("GET", META_PATH, response(METADATA)), ("GET", TABLE_PATH, response(public_page, text=True))])
    client = OEPClient(session=session)
    local = copy.deepcopy(METADATA)
    local["resources"][0]["title"] = "Correct"
    return client, session, local, client.prepare_metadata_upload(local, "example", tmp_path)


def review_plan(tmp_path, *, action="save", entries=None):
    session = FakeSession([("GET", TABLE_PATH, response(role_table(), text=True)),
                           ("GET", REVIEW_PATH, response(opr_page(), text=True))], authenticated=True)
    client = OPRClient(session=session)
    entries = copy.deepcopy(ENTRIES if entries is None else entries)
    return client, session, entries, client.prepare_review_upload(METADATA, entries, "example", tmp_path, action=action, review_id=7)


def test_metadata_dry_run_never_sends_token_or_write(tmp_path, monkeypatch):
    monkeypatch.setenv("OEP_API_TOKEN", "SECRET-TOKEN")
    client, session, local, plan = metadata_plan(tmp_path)
    result = client.execute_metadata_upload(plan, local)
    assert result["status"] == "dry_run"
    assert all(call[0] == "GET" for call in session.calls)
    assert (tmp_path / "metadata.remote.backup.json").exists()
    assert "Correct" in (tmp_path / "metadata.diff").read_text()
    assert "SECRET" not in "".join(p.read_text() for p in tmp_path.iterdir())


def test_metadata_valid_write_and_readback(tmp_path, monkeypatch):
    monkeypatch.setenv("OEP_API_TOKEN", "SECRET-TOKEN")
    client, session, local, plan = metadata_plan(tmp_path)
    session.steps += [("GET", TABLE_PATH, response("<p>Not reviewed</p>", text=True)),
                      ("GET", META_PATH, response(METADATA)), ("POST", META_PATH, response(local)),
                      ("GET", META_PATH, response(local))]
    assert client.execute_metadata_upload(plan, local, execute=True)["status"] == "verified"
    posts = [call for call in session.calls if call[0] == "POST"]
    assert posts[0][2]["json"] == local
    assert posts[0][2]["headers"] == {"Authorization": "Token SECRET-TOKEN"}
    assert "SECRET" not in "".join(p.read_text() for p in tmp_path.iterdir())


def test_metadata_local_and_remote_staleness_block_write(tmp_path, monkeypatch):
    monkeypatch.setenv("OEP_API_TOKEN", "secret")
    client, session, local, plan = metadata_plan(tmp_path)
    changed = copy.deepcopy(local)
    changed["resources"][0]["title"] = "Changed after preview"
    with pytest.raises(WorkflowError, match="local metadata changed"):
        client.execute_metadata_upload(plan, changed, execute=True)
    session.steps += [("GET", TABLE_PATH, response("<p>Not reviewed</p>", text=True)), ("GET", META_PATH, response(changed))]
    with pytest.raises(WorkflowError, match="Remote metadata changed"):
        client.execute_metadata_upload(plan, local, execute=True)
    assert all(call[0] == "GET" for call in session.calls)


@pytest.mark.parametrize("public_page", ['<p>Under review</p>', role_table()])
def test_metadata_cannot_bypass_active_opr(tmp_path, public_page):
    client, session, local, plan = metadata_plan(tmp_path, public_page=public_page)
    assert not plan["executable"]
    with pytest.raises(WorkflowError, match="OPR freezes"):
        client.execute_metadata_upload(plan, local, execute=True)
    assert all(call[0] == "GET" for call in session.calls)


@pytest.mark.parametrize("result, match", [(response({}, 403), "permission denied"),
                                        (response("not json", text=True), "malformed response"),
                                        (requests.Timeout("SECRET in upstream exception"), "outcome uncertain")])
def test_metadata_failed_or_uncertain_write_is_not_blindly_retried(tmp_path, monkeypatch, result, match):
    monkeypatch.setenv("OEP_API_TOKEN", "SECRET-TOKEN")
    client, session, local, plan = metadata_plan(tmp_path)
    session.steps += [("GET", TABLE_PATH, response("<p>Not reviewed</p>", text=True)),
                      ("GET", META_PATH, response(METADATA)), ("POST", META_PATH, result)]
    with pytest.raises(WorkflowError, match=match) as error:
        client.execute_metadata_upload(plan, local, execute=True)
    assert "SECRET" not in str(error.value)
    with pytest.raises(WorkflowError, match="already attempted"):
        client.execute_metadata_upload(plan, local, execute=True)
    assert sum(call[0] == "POST" for call in session.calls) == 1
    assert json.loads((tmp_path / "upload.receipt.json").read_text())["status"] == "not_verified_do_not_retry"


def test_metadata_server_normalization_is_visible(tmp_path, monkeypatch):
    monkeypatch.setenv("OEP_API_TOKEN", "secret")
    client, session, local, plan = metadata_plan(tmp_path)
    stored = copy.deepcopy(local)
    stored["resources"][0]["keywords"] = ["normalized"]
    session.steps += [("GET", TABLE_PATH, response("<p>Not reviewed</p>", text=True)),
                      ("GET", META_PATH, response(METADATA)), ("POST", META_PATH, response(stored)),
                      ("GET", META_PATH, response(stored))]
    assert client.execute_metadata_upload(plan, local, execute=True)["status"] == "stored_with_server_changes"


def test_metadata_unknown_review_status_reported(tmp_path):
    client, session, local, plan = metadata_plan(tmp_path, public_page="unrecognized layout")
    assert "review_status_unverified" in plan["limitations"]
    assert not plan["executable"]
    with pytest.raises(WorkflowError, match="OPR status.*unverified"):
        client.execute_metadata_upload(plan, local, execute=True)
    assert len(session.calls) == 2
    assert not (tmp_path / "upload.attempt.json").exists()


@pytest.mark.parametrize("page", [response("unknown layout", text=True), response({}, 503), requests.Timeout("read timeout")])
def test_metadata_opr_recheck_failure_blocks_write(tmp_path, page):
    client, session, local, plan = metadata_plan(tmp_path)
    assert plan["executable"]
    session.steps.append(("GET", TABLE_PATH, page))
    with pytest.raises(WorkflowError, match="OPR status.*unverified"):
        client.execute_metadata_upload(plan, local, execute=True)
    assert all(call[0] == "GET" for call in session.calls)
    assert not (tmp_path / "upload.attempt.json").exists()


def test_metadata_legacy_unverified_plan_cannot_bypass_guard(tmp_path):
    client, session, local, plan = metadata_plan(tmp_path, public_page="unrecognized layout")
    # Older versions marked an unknown review state executable. Its valid hash
    # must not substitute for a confirmed inactive review state.
    plan["executable"] = True
    plan["plan_hash"] = json_hash({key: value for key, value in plan.items() if key != "plan_hash"})
    with pytest.raises(WorkflowError, match="OPR status.*unverified"):
        client.execute_metadata_upload(plan, local, execute=True)
    assert len(session.calls) == 2
    assert not (tmp_path / "upload.attempt.json").exists()


@pytest.mark.parametrize("url", ["http://openenergyplatform.org", "https://u:p@openenergyplatform.org", "https://127.0.0.1", "https://localhost", "https://host.local", "https://openenergyplatform.org/path", "https://openenergyplatform.org?token=secret"])
def test_unsafe_base_urls_rejected(url):
    with pytest.raises(WorkflowError):
        safe_base_url(url)


def test_redirects_never_followed():
    redirect = response("", status=302, text=True)
    redirect.headers["Location"] = "https://attacker.example/"
    session = FakeSession([("GET", META_PATH, redirect)])
    with pytest.raises(WorkflowError, match="redirect refused"):
        OEPClient(session=session).read_metadata("example")
    assert len(session.calls) == 1


def test_plan_tampering_rejected(tmp_path):
    client, session, local, plan = metadata_plan(tmp_path)
    plan["table"] = "other"
    with pytest.raises(WorkflowError, match="plan hash changed"):
        client.execute_metadata_upload(plan, local, execute=True)
    assert len(session.calls) == 2


def test_review_mapping_save_and_submit_exact_protocol():
    page = parse_review_page(opr_page())
    for action in ("save", "submit"):
        payload, skipped, updates = build_review_payload(METADATA, ENTRIES, page, action=action, timestamp=123)
        assert payload["reviewType"] == action
        assert payload["reviewData"]["reviewFinished"] is False
        assert payload["reviewData"]["metadataVersion"] == "v1.6.0"
        mapped = {item["key"]: item for item in payload["reviewData"]["reviews"]}
        assert mapped["extent.name"]["category"] == "spatial"
        assert mapped["licenses.0.name"]["category"] == "license"
        assert mapped["title"]["fieldReview"][-1]["state"] == "suggestion"
        assert updates["title"]["newValue"] == "Correct"
        assert not skipped


def test_review_unknown_never_accepted():
    entries = copy.deepcopy(ENTRIES)
    entries[2]["decision"] = "unknown"
    page = parse_review_page(opr_page())
    payload, skipped, updates = build_review_payload(METADATA, entries, page, action="save")
    assert "licenses.0.name" not in updates
    assert skipped[-1]["reason"] == "unknown"
    with pytest.raises(WorkflowError, match="Unresolved"):
        build_review_payload(METADATA, entries, page, action="submit")


def test_review_self_or_wrong_role_blocked(tmp_path):
    session = FakeSession([("GET", TABLE_PATH, response(role_table(allowed=False), text=True))], authenticated=True)
    with pytest.raises(WorkflowError, match="account may be contributor"):
        OPRClient(session=session).prepare_review_upload(METADATA, ENTRIES, "example", tmp_path, review_id=7)
    assert len(session.calls) == 1


def test_review_requires_explicit_session(tmp_path):
    with pytest.raises(WorkflowError, match="authenticated session"):
        OPRClient(session=FakeSession()).prepare_review_upload(METADATA, ENTRIES, "example", tmp_path, review_id=7)


def test_review_frozen_snapshot_blocks_changed_local_metadata(tmp_path):
    session = FakeSession([("GET", TABLE_PATH, response(role_table(), text=True)),
                           ("GET", REVIEW_PATH, response(opr_page(title="Remote snapshot"), text=True))], authenticated=True)
    with pytest.raises(WorkflowError, match="frozen resource snapshot"):
        OPRClient(session=session).prepare_review_upload(METADATA, ENTRIES, "example", tmp_path, review_id=7)


def test_review_read_only_turn_blocks(tmp_path):
    session = FakeSession([("GET", TABLE_PATH, response(role_table(), text=True)),
                           ("GET", REVIEW_PATH, response(opr_page(read_only=True), text=True))], authenticated=True)
    with pytest.raises(WorkflowError, match="not the reviewer's turn"):
        OPRClient(session=session).prepare_review_upload(METADATA, ENTRIES, "example", tmp_path, review_id=7)


@pytest.mark.parametrize("action", ["save", "submit"])
def test_review_write_readback_and_dryrun(tmp_path, action):
    client, session, entries, plan = review_plan(tmp_path, action=action)
    assert client.execute_review_upload(plan, METADATA, entries)["status"] == "dry_run"
    assert len(session.calls) == 2
    history = {key: [value] for key, value in plan["updates"].items()}
    state = {key: value["state"] for key, value in plan["updates"].items()}
    session.steps += [("GET", TABLE_PATH, response(role_table(), text=True)),
                      ("GET", REVIEW_PATH, response(opr_page(), text=True)),
                      ("POST", REVIEW_PATH, response({"status": "success"})),
                      ("GET", REVIEW_PATH, response(opr_page(history=history, state=state, read_only=action == "submit"), text=True))]
    receipt = client.execute_review_upload(plan, METADATA, entries, execute=True)
    assert receipt["status"] == "verified"
    post = next(call for call in session.calls if call[0] == "POST")
    assert post[2]["headers"]["X-CSRFToken"] == "SECRET-CSRF"
    assert post[2]["json"]["reviewType"] == action
    assert "SECRET" not in "".join(p.read_text() for p in tmp_path.iterdir())


def test_review_uncertain_submission_cannot_retry(tmp_path):
    client, session, entries, plan = review_plan(tmp_path, action="submit")
    session.steps += [("GET", TABLE_PATH, response(role_table(), text=True)),
                      ("GET", REVIEW_PATH, response(opr_page(), text=True)),
                      ("POST", REVIEW_PATH, requests.Timeout("SECRET"))]
    with pytest.raises(WorkflowError, match="outcome uncertain"):
        client.execute_review_upload(plan, METADATA, entries, execute=True)
    with pytest.raises(WorkflowError, match="already attempted"):
        client.execute_review_upload(plan, METADATA, entries, execute=True)
    assert sum(call[0] == "POST" for call in session.calls) == 1


def test_review_stale_history_blocks_write(tmp_path):
    client, session, entries, plan = review_plan(tmp_path)
    old = {"title": [{"state": "rejected", "timestamp": 1}]}
    session.steps += [("GET", TABLE_PATH, response(role_table(), text=True)),
                      ("GET", REVIEW_PATH, response(opr_page(history=old), text=True))]
    with pytest.raises(WorkflowError, match="field history changed"):
        client.execute_review_upload(plan, METADATA, entries, execute=True)
    assert all(call[0] == "GET" for call in session.calls)


def test_review_structural_edits_and_multi_resources_rejected():
    page = parse_review_page(opr_page())
    root_edit = ENTRIES + [{"pointer": "/title", "decision": "conflict", "proposed_value": "Other"}]
    with pytest.raises(WorkflowError, match="structural/top-level edit"):
        build_review_payload(METADATA, root_edit, page)
    multi = copy.deepcopy(METADATA)
    multi["resources"].append(copy.deepcopy(multi["resources"][0]))
    with pytest.raises(WorkflowError, match="one resource"):
        build_review_payload(multi, ENTRIES, page)


def test_new_review_submit_requires_draft_id(tmp_path):
    with pytest.raises(WorkflowError, match="Save a new OPR draft first"):
        OPRClient(session=FakeSession(authenticated=True)).prepare_review_upload(METADATA, ENTRIES, "example", tmp_path, action="submit")


def test_new_review_save_discovers_id_without_guessing(tmp_path):
    create_path = "/database/example/open_peer_review/"
    session = FakeSession([("GET", TABLE_PATH, response(role_table(new=True), text=True)),
                           ("GET", create_path, response(opr_page(review_id=None), text=True))], authenticated=True)
    client = OPRClient(session=session)
    plan = client.prepare_review_upload(METADATA, ENTRIES, "example", tmp_path)
    history = {key: [value] for key, value in plan["updates"].items()}
    state = {key: value["state"] for key, value in plan["updates"].items()}
    session.steps += [("GET", TABLE_PATH, response(role_table(new=True), text=True)),
                      ("GET", create_path, response(opr_page(review_id=None), text=True)),
                      ("POST", create_path, response({"status": "success"})),
                      ("GET", TABLE_PATH, response(role_table(), text=True)),
                      ("GET", REVIEW_PATH, response(opr_page(history=history, state=state), text=True))]
    assert client.execute_review_upload(plan, METADATA, ENTRIES, execute=True)["review_id"] == 7


def test_review_claimed_success_with_wrong_readback_stops(tmp_path):
    client, session, entries, plan = review_plan(tmp_path, action="submit")
    session.steps += [("GET", TABLE_PATH, response(role_table(), text=True)),
                      ("GET", REVIEW_PATH, response(opr_page(), text=True)),
                      ("POST", REVIEW_PATH, response({"status": "success"})),
                      ("GET", REVIEW_PATH, response(opr_page(read_only=True), text=True))]
    with pytest.raises(WorkflowError, match="did not match readback"):
        client.execute_review_upload(plan, METADATA, entries, execute=True)
    assert json.loads((tmp_path / "upload.receipt.json").read_text())["status"] == "not_verified_do_not_retry"


def test_review_local_changes_or_payload_tampering_stop_before_network(tmp_path):
    client, session, entries, plan = review_plan(tmp_path)
    modified = copy.deepcopy(entries)
    modified[0]["comment"] = "Changed after preview"
    with pytest.raises(WorkflowError, match="local inputs changed"):
        client.execute_review_upload(plan, METADATA, modified, execute=True)
    payload_path = tmp_path / "opr.upload.json"
    payload = json.loads(payload_path.read_text())
    payload["reviewType"] = "finished"
    payload_path.write_text(json.dumps(payload))
    with pytest.raises(WorkflowError, match="payload changed"):
        client.execute_review_upload(plan, METADATA, entries, execute=True)
    assert len(session.calls) == 2


def test_metadata_post_and_get_mismatch_remains_uncertain(tmp_path, monkeypatch):
    monkeypatch.setenv("OEP_API_TOKEN", "secret")
    client, session, local, plan = metadata_plan(tmp_path)
    session.steps += [("GET", TABLE_PATH, response("<p>Not reviewed</p>", text=True)),
                      ("GET", META_PATH, response(METADATA)), ("POST", META_PATH, response(local)),
                      ("GET", META_PATH, response(METADATA))]
    with pytest.raises(WorkflowError, match="response and readback differ"):
        client.execute_metadata_upload(plan, local, execute=True)
    assert (tmp_path / "metadata.readback.json").exists()


def test_upload_plans_bind_to_their_file_after_relocation(tmp_path):
    import shutil
    original = tmp_path / "original"
    client, session, entries, plan = review_plan(original)
    assert str(tmp_path) not in (original / "upload.plan.json").read_text()
    moved = tmp_path / "moved"
    shutil.move(original, moved)
    assert client.execute_review_upload(moved / "upload.plan.json", METADATA, entries)["status"] == "dry_run"
    (moved / "opr.upload.json").write_text("{}")
    with pytest.raises(WorkflowError, match="payload changed"):
        client.execute_review_upload(moved / "upload.plan.json", METADATA, entries)


def test_metadata_plan_directory_is_runtime_only(tmp_path):
    import shutil
    original = tmp_path / "original"
    client, session, local, plan = metadata_plan(original)
    assert str(tmp_path) not in (original / "upload.plan.json").read_text()
    moved = tmp_path / "moved"
    shutil.move(original, moved)
    (moved / "upload.attempt.json").write_text("{}")
    with pytest.raises(WorkflowError, match="already attempted"):
        client.execute_metadata_upload(moved / "upload.plan.json", local, execute=True)


def cli_upload_case(tmp_path, monkeypatch, operation):
    """Prepare real plans and adapters, using injected HTTP responses only."""
    from oepmeta import oep_client, opr_client
    from oepmeta.common import write_json
    directory = tmp_path / "prepared"
    if operation == "metadata-upload":
        from oepmeta.profile import profile_data
        from oepmeta.validate import build_skeleton
        data = tmp_path / "data.csv"
        data.write_text("power\n1\n")
        remote = build_skeleton(profile_data(data), table_name="example")
        local = copy.deepcopy(remote)
        local["resources"][0]["title"] = "Correct"
        session = FakeSession([("GET", META_PATH, response(remote)),
                               ("GET", TABLE_PATH, response("<p>Not reviewed</p>", text=True))])
        client = OEPClient(session=session)
        plan = client.prepare_metadata_upload(local, "example", directory)
        session.steps += [("GET", TABLE_PATH, response("<p>Not reviewed</p>", text=True)),
                          ("GET", META_PATH, response(remote)), ("POST", META_PATH, response(local)),
                          ("GET", META_PATH, response(local))]
        monkeypatch.setattr(oep_client, "OEPClient", lambda **kwargs: client)
        monkeypatch.setenv("OEP_API_TOKEN", "fixture-token")
        extra = []
    else:
        client, session, entries, plan = review_plan(directory)
        local = METADATA
        history = {key: [value] for key, value in plan["updates"].items()}
        state = {key: value["state"] for key, value in plan["updates"].items()}
        session.steps += [("GET", TABLE_PATH, response(role_table(), text=True)),
                          ("GET", REVIEW_PATH, response(opr_page(), text=True)),
                          ("POST", REVIEW_PATH, response({"status": "success"})),
                          ("GET", REVIEW_PATH, response(opr_page(history=history, state=state), text=True))]
        review = tmp_path / "review.json"
        write_json(review, {"metadata_hash": json_hash(local), "entries": entries})
        monkeypatch.setattr(opr_client, "OPRClient", lambda **kwargs: client)
        extra = ["--review", str(review), "--action", "save", "--review-id", "7"]
    metadata = tmp_path / "metadata.json"
    write_json(metadata, local)
    args = [operation, "--metadata", str(metadata), "--table", "example", "--execute"] + extra
    return directory, session, args


@pytest.mark.parametrize("operation", ["metadata-upload", "review-upload"])
@pytest.mark.parametrize("relocate", [False, True])
def test_cli_executes_plan_from_another_working_directory(tmp_path, monkeypatch, capsys, operation, relocate):
    import os
    import shutil
    import oep_metadata
    directory, session, args = cli_upload_case(tmp_path, monkeypatch, operation)
    if relocate:
        moved = tmp_path / "relocated"
        shutil.move(directory, moved)
        directory = moved
    working = tmp_path / "working"
    working.mkdir()
    monkeypatch.chdir(working)
    args += ["--out", os.path.relpath(directory), "--plan", os.path.relpath(directory / "upload.plan.json")]
    assert oep_metadata.main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "verified"
    assert sum(call[0] == "POST" for call in session.calls) == 1
    assert not session.steps
    assert (directory / "upload.receipt.json").is_file()


@pytest.mark.parametrize("operation", ["metadata-upload", "review-upload"])
@pytest.mark.parametrize("mismatch", ["table", "directory", "hash"])
def test_cli_rejects_plan_mismatch_before_requests(tmp_path, monkeypatch, capsys, operation, mismatch):
    import oep_metadata
    directory, session, args = cli_upload_case(tmp_path, monkeypatch, operation)
    args += ["--out", str(directory), "--plan", str(directory / "upload.plan.json")]
    if mismatch == "table":
        args[args.index("--table") + 1] = "different"
    elif mismatch == "directory":
        args[args.index("--out") + 1] = str(tmp_path / "different")
    else:
        args += ["--plan-hash", "unexpected"]
    requests_before = len(session.calls)
    assert oep_metadata.main(args) == 2
    assert "error" in json.loads(capsys.readouterr().err)
    assert len(session.calls) == requests_before


@pytest.mark.parametrize("option,value", [("--action", "submit"), ("--review-id", "8")])
def test_cli_rejects_different_review_target(tmp_path, monkeypatch, capsys, option, value):
    import oep_metadata
    directory, session, args = cli_upload_case(tmp_path, monkeypatch, "review-upload")
    args += ["--out", str(directory), "--plan", str(directory / "upload.plan.json")]
    args[args.index(option) + 1] = value
    requests_before = len(session.calls)
    assert oep_metadata.main(args) == 2
    assert "error" in json.loads(capsys.readouterr().err)
    assert len(session.calls) == requests_before
