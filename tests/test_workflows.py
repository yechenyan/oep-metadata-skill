"""Tool contracts: the AI chooses actions; tools gate evidence and delivery."""

import copy
import shutil
from pathlib import Path

import pytest

from oepmeta import workflows as w
from oepmeta.common import WorkflowError, get_pointer, json_hash, load_json, write_json


@pytest.fixture
def inputs(tmp_path):
    data = tmp_path / "power.csv"
    data.write_text("year,power\n2035,1.2\n2040,2.3\n")
    background = tmp_path / "background.txt"
    background.write_text("Capacity projections. Installed electrical generation capacity in GW for 2035 and 2040. License and creator not supplied.")
    return data, background


def start(tmp_path, inputs, intent="generate-review", **kwargs):
    out = tmp_path / intent
    w.collect(intent, out, data=inputs[0], background=[inputs[1]], **kwargs)
    return out


def context(out):
    return w.inspect(out)["context"]


def generation(out, title="Capacity projections"):
    ctx = context(out)
    metadata = copy.deepcopy(ctx["metadata"])
    metadata["resources"][0]["title"] = title
    eid = next(e["id"] for e in ctx["evidence"] if e["kind"] == "background")
    return {"input_hash": ctx["input_hash"], "metadata": metadata,
            "provenance": [{"pointer": "/resources/0/title", "status": "supported", "evidence_ids": [eid], "rationale": "Title stated in supplied source."}]}


def review(out, *, conflict=None, unknown=None, proposed="Capacity projections"):
    ctx = context(out)
    eid = next(e["id"] for e in ctx["evidence"] if e["kind"] == "background")
    entries = []
    for f in ctx["review_fields"]:
        entry = {"pointer": f["pointer"], "decision": "supported", "comment": "Synthetic tool-contract fixture; not a semantic evaluation.", "evidence_ids": [eid]}
        if f["pointer"] == conflict:
            entry.update(decision="conflict", comment="Contradicts supplied source.", proposed_value=proposed)
        if f["pointer"] == unknown:
            entry.update(decision="unknown", comment="Need a source before deciding.", evidence_ids=[])
        entries.append(entry)
    return {"input_hash": ctx["input_hash"], "metadata_hash": ctx["metadata_hash"], "entries": entries, "summary": "Fixture review."}


def patch(out, value="Capacity projections"):
    ctx = context(out)
    eid = next(e["id"] for e in ctx["evidence"] if e["kind"] == "background")
    return {"input_hash": ctx["input_hash"], "base_hash": ctx["metadata_hash"],
            "patches": [{"op": "replace", "pointer": "/resources/0/title", "old_value": ctx["metadata"]["resources"][0]["title"],
                         "value": value, "evidence_ids": [eid], "reason": "Match source."}]}


def summary(**kwargs):
    return {"overview": "Metadata prepared from the supplied material.", "needs_attention": ["Contact and rights holder require confirmation before publication."], "notes": ["Unsubstantiated facts remain null."], **kwargs}


def assert_no_sidecars(out):
    for name in ("questions.json", "validation.json", "agent_request.json", "review_sheet.md", "generation_sheet.md"):
        assert not list(out.rglob(name))


def test_ai_explicitly_selects_each_action_and_delivery(tmp_path, inputs):
    out = start(tmp_path, inputs, "generate")
    assert not list(out.glob("*.json"))
    before = context(out)["input_hash"]
    accepted = w.record_metadata(out, generation(out))
    assert accepted["ok"] and accepted["input_hash"] == context(out)["input_hash"] != before
    assert w.inspect(out)["state"]["status"] == "open"
    assert w.inspect(out)["review"] is None
    assert not (out / "metadata.json").exists()
    result = w.deliver(out, summary())
    assert result["ok"]
    assert set(result["outputs"]) == {"metadata.json", "summary.md"}
    assert w.check(out / "metadata.json", out=out)["ok"]
    assert "Contact and rights holder" in (out / "summary.md").read_text()
    assert_no_sidecars(out)
    with pytest.raises(WorkflowError, match="closed"):
        w.record_metadata(out, generation(out))


@pytest.mark.parametrize("bad_date", ["2026-13-40", 20261025])
def test_ai_can_correct_failed_checks_without_exporting_invalid_metadata(tmp_path, inputs, bad_date):
    import oep_metadata
    out = start(tmp_path, inputs, "generate")
    candidate = generation(out)
    candidate["metadata"]["resources"][0]["publicationDate"] = bad_date
    candidate["provenance"].append({**candidate["provenance"][0], "pointer": "/resources/0/publicationDate"})
    before = context(out)
    path = tmp_path / "candidate.json"
    write_json(path, candidate)
    assert oep_metadata.main(["record-metadata", "--out", str(out), "--candidate", str(path)]) == 1
    assert context(out) == before
    assert not w.deliver(out, summary())["ok"]
    assert not (out / "metadata.json").exists()
    candidate["metadata"]["resources"][0]["publicationDate"] = "2026-10-25"
    write_json(path, candidate)
    assert oep_metadata.main(["record-metadata", "--out", str(out), "--candidate", str(path)]) == 0
    assert w.deliver(out, summary())["ok"]
    assert_no_sidecars(out)


def test_combined_requires_current_independent_review(tmp_path, inputs):
    out = start(tmp_path, inputs)
    w.record_metadata(out, generation(out, "Wrong title"))
    assert w.deliver(out, summary())["error"] == "current_independent_review_required"
    with pytest.raises(WorkflowError, match="independent"):
        w.record_review(out, review(out))
    w.record_review(out, review(out, conflict="/resources/0/title"), independent=True)
    assert w.deliver(out, summary())["error"] == "unresolved_conflicts"
    old = context(out)["input_hash"]
    assert w.apply_patch(out, patch(out))["ok"]
    assert context(out)["input_hash"] != old
    assert w.inspect(out)["review"] is None
    assert w.deliver(out, summary())["error"] == "current_independent_review_required"
    w.record_review(out, review(out, unknown="/resources/0/format"), independent=True)
    result = w.deliver(out, summary())
    assert set(result["outputs"]) == {"metadata.json", "summary.md", "review.md"}
    assert result["status"] == "delivered_with_notes"
    assert_no_sidecars(out)


@pytest.mark.parametrize("mutation,match", [
    (lambda c: c["entries"].pop(), "Missing review pointers"),
    (lambda c: c.update(input_hash="stale"), "input_hash"),
    (lambda c: c.update(metadata_hash="stale"), "metadata_hash"),
    (lambda c: c["entries"].append(c["entries"][0]), "duplicate"),
    (lambda c: c["entries"][0].update(evidence_ids=["invented"]), "Unknown evidence"),
])
def test_review_coverage_and_bindings(tmp_path, inputs, mutation, match):
    out = start(tmp_path, inputs)
    w.record_metadata(out, generation(out))
    candidate = review(out)
    mutation(candidate)
    with pytest.raises(WorkflowError, match=match):
        w.record_review(out, candidate, independent=True)


@pytest.mark.parametrize("mutation,match", [
    (lambda c: c["patches"][0].update(pointer="/name"), "outside"),
    (lambda c: c["patches"][0].update(old_value="stale"), "old_value"),
    (lambda c: c.update(base_hash="stale"), "base_hash"),
    (lambda c: c["patches"].append(c["patches"][0]), "Overlapping"),
    (lambda c: c["patches"][0].update(evidence_ids=[]), "requires evidence"),
])
def test_patch_scope_and_evidence(tmp_path, inputs, mutation, match):
    out = start(tmp_path, inputs)
    w.record_metadata(out, generation(out, "Wrong title"))
    w.record_review(out, review(out, conflict="/resources/0/title"), independent=True)
    candidate = patch(out)
    mutation(candidate)
    with pytest.raises(WorkflowError, match=match):
        w.apply_patch(out, candidate)


def test_limits_and_cycles_return_control_to_ai(tmp_path, inputs):
    out = start(tmp_path, inputs, "generate", max_changes=3)
    assert w.record_metadata(out, generation(out, "A"))["ok"]
    assert w.record_metadata(out, generation(out, "A"))["error"] == "no_progress_or_repeated_version"
    assert w.record_metadata(out, generation(out, "B"))["ok"]
    assert w.record_metadata(out, generation(out, "A"))["error"] == "no_progress_or_repeated_version"
    assert w.record_metadata(out, generation(out, "C"))["ok"]
    assert w.record_metadata(out, generation(out, "D"))["error"] == "change_limit"
    assert w.inspect(out)["state"]["status"] == "open"
    assert w.stop(out, summary(overview="Evidence is insufficient."))["status"] == "stopped"
    assert not (out / "metadata.json").exists()
    assert_no_sidecars(out)


def test_generation_rejects_unsubstantiated_claims_and_observed_structure_changes(tmp_path, inputs):
    out = start(tmp_path, inputs, "generate")
    candidate = generation(out)
    candidate["provenance"] = []
    with pytest.raises(WorkflowError, match="requires supported provenance"):
        w.record_metadata(out, candidate)
    candidate = generation(out)
    candidate["metadata"]["resources"][0]["schema"]["fields"][0]["name"] = "invented"
    with pytest.raises(WorkflowError, match="observed field"):
        w.record_metadata(out, candidate)
    with pytest.raises(WorkflowError, match="excludes existing"):
        w.collect("generate", tmp_path / "leaked", data=inputs[0], metadata="answer.json")


@pytest.mark.parametrize("pointer,value", [
    ("/resources/0/licenses", [{"name": "CC-BY-4.0"}]),
    ("/metaMetadata/metadataLicense/name", "CC0-1.0"),
    ("/resources/0/sources", [{"authors": ["Fixture Author"]}]),
    ("/resources/0/schema/fields/0/nullable", False),
])
def test_profile_cannot_establish_license_or_not_null_constraint(tmp_path, inputs, pointer, value):
    from oepmeta.common import leaves, set_pointer
    out = start(tmp_path, inputs, "generate")
    candidate = generation(out)
    set_pointer(candidate["metadata"], pointer, value)
    eid = next(e["id"] for e in context(out)["evidence"] if e["kind"] == "data_profile")
    candidate["provenance"] += [{"pointer": p, "status": "supported", "evidence_ids": [eid], "rationale": "Unsupported fixture inference."} for p, _ in leaves(value, pointer)]
    with pytest.raises(WorkflowError, match="documentary"):
        w.record_metadata(out, candidate)
    assert context(out)["metadata"]["resources"][0]["schema"]["fields"][0]["nullable"] is None


def test_database_constraints_override_observations(tmp_path, inputs, monkeypatch):
    from oepmeta import collect
    from oepmeta.profile import profile_data
    prof = profile_data(inputs[0])
    monkeypatch.setattr(collect, "collect_inputs", lambda **kwargs: {
        "profile": prof, "metadata": None, "evidence": [], "snapshots": [],
        "db_schema": {"columns": {"year": {"ordinal_position": 1, "data_type": "smallint", "is_nullable": True},
                                  "power": {"ordinal_position": 2, "data_type": "numeric", "is_nullable": False}}}})
    out = tmp_path / "database"
    w.collect("generate", out, table="capacities")
    fields = context(out)["metadata"]["resources"][0]["schema"]["fields"]
    assert [(f["type"], f["nullable"]) for f in fields] == [("smallint", True), ("numeric", False)]


def test_evidence_addition_invalidates_review_and_candidates(tmp_path, inputs):
    out = start(tmp_path, inputs)
    w.record_metadata(out, generation(out))
    w.record_review(out, review(out), independent=True)
    stale = generation(out)
    extra = tmp_path / "extra.txt"
    extra.write_text("Further source declaration.")
    added = w.add_evidence(out, extra)
    assert added["input_hash"] == context(out)["input_hash"] != stale["input_hash"]
    assert w.inspect(out)["review"] is None
    with pytest.raises(WorkflowError, match="input_hash"):
        w.record_metadata(out, stale)


def test_snapshot_tampering_refused(tmp_path, inputs):
    out = start(tmp_path, inputs)
    snapshot = context(out)["snapshots"][0]["path"]
    (out / snapshot).write_text("tampered")
    for action in (lambda: w.inspect(out), lambda: w.deliver(out, summary()), lambda: w.stop(out, summary())):
        with pytest.raises(WorkflowError, match="snapshot changed"):
            action()


def test_review_tampering_refused(tmp_path, inputs):
    out = start(tmp_path, inputs)
    w.record_metadata(out, generation(out))
    w.record_review(out, review(out), independent=True)
    path = out / ".work/review.json"
    opinion = load_json(path)
    opinion["summary"] = "tampered"
    write_json(path, opinion)
    with pytest.raises(WorkflowError, match="Review is stale or changed"):
        w.deliver(out, summary())


def test_relocated_run_and_evidence_remain_usable(tmp_path, inputs):
    index = tmp_path / "ontology.json"
    write_json(index, {"version": "fixture", "terms": {}})
    out = start(tmp_path, inputs, "generate", ontology_index=index)
    extra = tmp_path / "extra.txt"
    extra.write_text("Additional declaration.")
    w.add_evidence(out, extra)
    for artifact in out.rglob("*"):
        if artifact.is_file():
            assert str(tmp_path) not in artifact.read_text()
    for evidence in context(out)["evidence"]:
        if evidence["id"].startswith("ev-"):
            assert evidence["id"] == "ev-" + json_hash({k: evidence[k] for k in ("kind", "content", "source")})[:16]
    moved = tmp_path / "relocated"
    shutil.move(out, moved)
    assert w.record_metadata(moved, generation(moved))["ok"]
    assert w.deliver(moved, summary())["ok"]
    assert all(not Path(s["path"]).is_absolute() for s in context(moved)["snapshots"])


def test_review_only_preserves_original_and_exports_valid_suggestion(tmp_path, inputs):
    generated = start(tmp_path, inputs, "generate")
    w.record_metadata(generated, generation(generated, "Wrong title"))
    w.deliver(generated, summary())
    source = generated / "metadata.json"
    original = source.read_bytes()
    out = tmp_path / "review"
    w.collect("review", out, metadata=source, data=inputs[0], background=[inputs[1]])
    with pytest.raises(WorkflowError, match="Review-only"):
        w.record_metadata(out, generation(out))
    w.record_review(out, review(out, conflict="/resources/0/title"))
    result = w.deliver(out, summary())
    assert set(result["outputs"]) == {"review.md", "summary.md", "metadata.suggested.json"}
    assert source.read_bytes() == original
    assert w.check(out / "metadata.suggested.json", out=out)["ok"]
    assert_no_sidecars(out)


def test_review_does_not_export_mechanically_invalid_suggestion(tmp_path, inputs):
    generated = start(tmp_path, inputs, "generate")
    w.record_metadata(generated, generation(generated))
    w.deliver(generated, summary())
    out = tmp_path / "review"
    w.collect("review", out, metadata=generated / "metadata.json", background=[inputs[1]])
    result = w.record_review(out, review(out, conflict="/resources/0/schema/fields/0/type", proposed=17))
    # The review is retained, but an invalid suggestion must never be a metadata deliverable.
    assert result["ok"]
    assert not result["suggested_checks"]["mechanical_valid"]
    assert w.deliver(out, summary())["ok"]
    assert not (out / "metadata.suggested.json").exists()
    assert "not exported" in (out / "summary.md").read_text()


def test_summary_is_concise_and_not_a_field_question_dump(tmp_path, inputs):
    out = start(tmp_path, inputs, "generate")
    w.record_metadata(out, generation(out))
    with pytest.raises(WorkflowError, match="at most eight"):
        w.deliver(out, summary(needs_attention=["One question"] * 29))
    assert not (out / "metadata.json").exists()


def test_report_groups_decisions_and_renders_model_text_literally():
    report = {"metadata_hash": "fixture", "summary": "</details>\n# Fake heading", "entries": [
        {"pointer": "/title", "decision": "conflict", "comment": "<script>alert(1)</script>", "evidence_ids": ["source-1"], "proposed_value": "<em>literal</em>`x`"},
        {"pointer": "/description", "decision": "unknown", "comment": "Need evidence.", "evidence_ids": []},
        {"pointer": "/type", "decision": "supported", "comment": "Source matches.", "evidence_ids": ["source-1"]},
        {"pointer": "/contact", "decision": "not_applicable", "comment": "Reason given.", "evidence_ids": []},
    ]}
    text = w.render_review_report(report)
    assert w.review_decision_counts(report["entries"]) == dict.fromkeys(w.DECISIONS, 1)
    assert "Field decisions needing attention: **2**" in text
    assert "Unknown is not a confirmed error" in text
    assert text.count("</details>") == 2
    assert "<script>" not in text and "<em>" not in text and "\n# Fake heading" not in text
    assert "&lt;em&gt;literal&lt;/em&gt;`x`" in text
    assert "<details open" not in text
    assert "validation.json" not in text


def test_report_handles_no_problems_without_inventing_any():
    text = w.render_review_report({"metadata_hash": "fixture", "entries": []})
    assert "Field decisions needing attention: **0**" in text
    assert "## Conflicts - inspect or correct (0)" in text
    assert "## Unresolved - needs evidence (0)" in text


def test_json_pointer_zero_false_and_escaping():
    document = {"a/b": [{"~": False}, 0]}
    assert get_pointer(document, "/a~1b/0/~0") is False
    assert get_pointer(document, "/a~1b/1") == 0
    with pytest.raises(WorkflowError):
        get_pointer(document, "/a~1b/-1")


def test_ai_added_type_can_be_corrected_after_independent_review(tmp_path):
    data = tmp_path / "empty.csv"
    data.write_text("value\n\"\"\n")
    background = tmp_path / "source.md"
    background.write_text("The value column represents text. No observed values are available.")
    out = tmp_path / "unknown-type"
    w.collect("generate-review", out, data=data, background=[background])
    ctx = context(out)
    assert ctx["metadata"]["resources"][0]["schema"]["fields"][0]["type"] is None
    candidate = generation(out)
    candidate["metadata"]["resources"][0]["schema"]["fields"][0]["type"] = "integer"
    candidate["provenance"].append({**candidate["provenance"][0], "pointer": "/resources/0/schema/fields/0/type"})
    assert w.record_metadata(out, candidate)["ok"]
    pointer = "/resources/0/schema/fields/0/type"
    w.record_review(out, review(out, conflict=pointer, proposed="string"), independent=True)
    correction = patch(out)
    correction["patches"][0].update(pointer=pointer, old_value="integer", value="string")
    assert w.apply_patch(out, correction)["ok"]
    assert get_pointer(context(out)["metadata"], pointer) == "string"
    w.record_review(out, review(out, conflict=pointer, proposed="number"), independent=True)
    revised = generation(out)
    revised["metadata"]["resources"][0]["schema"]["fields"][0]["type"] = "number"
    revised["provenance"].append({**revised["provenance"][0], "pointer": pointer})
    assert w.record_metadata(out, revised)["ok"]


def test_outcome_is_consistent_between_response_and_persisted_state(tmp_path, inputs):
    out = start(tmp_path, inputs, "generate")
    w.record_metadata(out, generation(out))
    result = w.deliver(out, summary())
    state = w.inspect(out)["state"]
    assert state["status"] == "delivered"
    assert state["outcome"] == result["status"] == "delivered_with_notes"


def test_list_form_database_columns_are_collected_and_checked(tmp_path, inputs, monkeypatch):
    from oepmeta import collect
    from oepmeta.profile import profile_data
    monkeypatch.setattr(collect, "collect_inputs", lambda **kwargs: {
        "profile": profile_data(inputs[0]), "metadata": None, "evidence": [], "snapshots": [],
        "db_schema": {"columns": [{"name": "year", "data_type": "smallint", "is_nullable": False},
                                  {"name": "power", "data_type": "numeric", "is_nullable": True}]}})
    out = tmp_path / "database-list"
    collected = w.collect("generate", out, table="sample_table")
    fields = collected["context"]["metadata"]["resources"][0]["schema"]["fields"]
    assert [(f["name"], f["type"], f["nullable"]) for f in fields] == [("year", "smallint", False), ("power", "numeric", True)]
    assert collected["checks"]["mechanical_valid"]


@pytest.mark.parametrize("resources", [None, 3, "invalid", [{"schema": {"fields": [{"name": []}]}}]])
def test_review_reports_invalid_original_instead_of_crashing(tmp_path, resources):
    metadata = tmp_path / "invalid.json"
    write_json(metadata, {"metaMetadata": {"metadataVersion": "OEMetadata-2.0.4"}, "resources": resources})
    out = tmp_path / "invalid-review"
    result = w.collect("review", out, metadata=metadata)
    assert not result["checks"]["mechanical_valid"]
    ctx = context(out)
    assert isinstance(ctx["review_fields"], list)
    candidate = {"input_hash": ctx["input_hash"], "metadata_hash": ctx["metadata_hash"], "entries": [
        {"pointer": f["pointer"], "decision": "unknown", "comment": "The structure is invalid; correct the reported program errors.", "evidence_ids": []}
        for f in ctx["review_fields"]]}
    assert w.record_review(out, candidate)["ok"]
    assert w.deliver(out, summary(overview="Original metadata contains program errors."))["ok"]
    assert "errors reported in the review" in (out / "summary.md").read_text()
    assert "errors;" in (out / "review.md").read_text()
    assert not (out / "metadata.json").exists()


def test_documented_type_can_correct_profile_inference(tmp_path, inputs):
    out = start(tmp_path, inputs, "generate")
    candidate = generation(out)
    pointer = "/resources/0/schema/fields/0/type"
    # A profile's inferred value type is evidence, not an immutable database declaration.
    candidate["metadata"]["resources"][0]["schema"]["fields"][0]["type"] = "string"
    candidate["provenance"].append({**candidate["provenance"][0], "pointer": pointer})
    result = w.record_metadata(out, candidate)
    assert result["ok"]
    assert any(i["code"] == "observed_type_conflict" and i["severity"] == "warning" for i in result["checks"]["issues"])
    assert get_pointer(context(out)["metadata"], pointer) == "string"


def test_source_author_can_use_an_explicit_declaration(tmp_path, inputs):
    out = start(tmp_path, inputs, "generate")
    declaration = tmp_path / "authors.md"
    declaration.write_text("The supplied source material was written by Fixture Author.")
    evidence = w.add_evidence(out, declaration, kind="declaration")
    candidate = generation(out)
    candidate["metadata"]["resources"][0]["sources"] = [{"authors": ["Fixture Author"]}]
    candidate["provenance"].append({"pointer": "/resources/0/sources/0/authors/0", "status": "supported",
                                    "evidence_ids": [evidence["evidence_id"]], "rationale": "Author explicitly named in the declaration."})
    assert w.record_metadata(out, candidate)["ok"]
    assert w.deliver(out, summary())["ok"]


@pytest.mark.parametrize("dtype", ["geometry(Point, 4326)", "char"])
def test_generation_accepts_exact_declared_database_type(tmp_path, inputs, monkeypatch, dtype):
    from oepmeta import collect
    from oepmeta.profile import profile_data
    monkeypatch.setattr(collect, "collect_inputs", lambda **kwargs: {
        "profile": profile_data(inputs[0]), "metadata": None, "evidence": [], "snapshots": [],
        "db_schema": {"columns": {"year": {"ordinal_position": 1, "data_type": dtype},
                                  "power": {"ordinal_position": 2, "data_type": "numeric"}}}})
    out = tmp_path / "typed-database"
    w.collect("generate", out, table="sample_table")
    ctx = context(out)
    assert w.record_metadata(out, {"input_hash": ctx["input_hash"], "metadata": ctx["metadata"], "provenance": []})["ok"]
    assert w.deliver(out, summary())["ok"]
