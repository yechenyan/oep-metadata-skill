"""Core negative controls: values, coverage, validation and provenance."""

import copy
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/oep-metadata/scripts"))

from oepmeta import collect, ontology
from oepmeta.common import WorkflowError, file_hash
from oepmeta.profile import profile_data
from oepmeta.validate import build_skeleton, validate_metadata


def csv_profile(tmp_path, text="id,value,unit\n0,0,MW\n1,,MWh\n"):
    source = tmp_path / "input.csv"
    source.write_text(text)
    return profile_data(source)


def test_json_null_boolean_and_zero_are_distinct(tmp_path):
    path = tmp_path / "rows.json"
    path.write_text(json.dumps([{"v": False, "x": 0}, {"v": 0, "x": None}, {"v": "0"}]))
    prof = profile_data(path)
    assert prof["row_count"] == 3
    assert prof["columns"]["v"]["distinct_count"] == 3
    assert prof["columns"]["v"]["null_count"] == 0
    assert prof["columns"]["v"]["type"] == "mixed"
    assert prof["columns"]["x"]["null_count"] == 2
    assert prof["columns"]["x"]["min"] == 0


def test_csv_only_empty_cells_are_null(tmp_path):
    prof = csv_profile(tmp_path, "id,value\n001,0\n002,NA\n003,/\n004,null\n005,\n")
    assert prof["columns"]["id"]["type"] == "string"
    assert prof["columns"]["value"]["null_count"] == 1
    assert prof["columns"]["value"]["distinct_count"] == 4


def test_csv_boolean_and_zero_preserve_values(tmp_path):
    prof = csv_profile(tmp_path, "flag,count\nfalse,0\ntrue,1\n")
    assert prof["columns"]["flag"]["type"] == "boolean"
    assert prof["columns"]["flag"]["null_count"] == 0
    assert prof["columns"]["flag"]["top_values"] == [{"value": False, "count": 1}, {"value": True, "count": 1}]
    assert prof["columns"]["count"]["min"] == 0


def test_csv_duplicate_headers_and_ragged_rows_rejected(tmp_path):
    with pytest.raises(WorkflowError, match="Duplicate"):
        csv_profile(tmp_path, "x,x\n1,2\n")
    with pytest.raises(WorkflowError, match="cells"):
        csv_profile(tmp_path, "x,y\n1,2,3\n")


def test_csv_semicolon_and_prefix_coverage(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_text("year;value\n2030;1\n2050;2\n2100;\n")
    prof = profile_data(path, max_rows=2)
    assert prof["delimiter"] == ";"
    assert prof["row_count"] == 3
    assert prof["coverage"]["scanned_rows"] == 2
    assert prof["coverage"]["complete"] is False
    assert prof["columns"]["value"]["null_count"] == 0
    assert prof["coverage"]["fraction"] == pytest.approx(2 / 3)


def test_json_late_columns_and_invalid_data(tmp_path):
    path = tmp_path / "rows.json"
    path.write_text('[{"a":1},{"a":2,"b":false}]')
    prof = profile_data(path)
    assert prof["columns"]["b"]["null_count"] == 1
    assert prof["columns"]["b"]["top_values"] == [{"value": False, "count": 1}]
    path.write_text('[{"v":NaN}]')
    with pytest.raises(WorkflowError):
        profile_data(path)
    path.write_text('{"data":[]}')
    with pytest.raises(WorkflowError, match="array"):
        profile_data(path)


def test_skeleton_uses_omi_and_does_not_leak_template_facts(tmp_path):
    prof = csv_profile(tmp_path)
    metadata = build_skeleton(prof, "sample_table")
    result = validate_metadata(metadata, profile=prof)
    assert result["schema_valid"], result["issues"]
    assert result["format_valid"], result["issues"]
    resource = metadata["resources"][0]
    assert "boundingBox" not in resource["spatial"]["extent"]
    assert resource["embargoPeriod"]["isActive"] is None
    assert resource["licenses"] == []
    assert metadata["metaMetadata"]["metadataLicense"]["name"] is None
    assert resource["schema"]["fields"][0]["name"] == "id"
    assert resource["schema"]["fields"][0]["type"] == "integer"


def test_partial_skeleton_does_not_assert_no_nulls(tmp_path):
    path = tmp_path / "rows.csv"
    path.write_text("id\n1\n2\n")
    prof = profile_data(path, max_rows=1)
    metadata = build_skeleton(prof)
    assert metadata["resources"][0]["schema"]["fields"][0]["nullable"] is None


def test_schema_and_format_negative_controls(tmp_path):
    metadata = build_skeleton(csv_profile(tmp_path))
    broken = copy.deepcopy(metadata)
    broken["resources"] = False
    assert validate_metadata(broken)["schema_valid"] is False
    broken = copy.deepcopy(metadata)
    broken["resources"][0]["publicationDate"] = "2026-13-40"
    result = validate_metadata(broken)
    assert result["format_valid"] is False
    assert any(i["pointer"] == "/resources/0/publicationDate" for i in result["issues"])
    broken["resources"][0]["publicationDate"] = "2050-01-01"
    broken["resources"][0]["temporal"]["referenceDate"] = "2050-01-01"
    assert validate_metadata(broken)["format_valid"] is True
    broken["resources"][0]["subject"] = [{"@id": "this is not a URI", "name": "term"}]
    assert validate_metadata(broken)["format_valid"] is False
    broken["resources"][0]["subject"] = []
    broken["resources"][0]["temporal"]["timeseries"] = [{"start": "2050-13-50T99:99:99Z"}]
    assert validate_metadata(broken)["format_valid"] is False


def test_spdx_independent_positive_and_fake_negative(tmp_path):
    metadata = build_skeleton(csv_profile(tmp_path))
    metadata["resources"][0]["licenses"] = [{"name": "CC-BY-4.0"}]
    assert not any(i["code"] == "spdx_unknown" for i in validate_metadata(metadata)["issues"])
    metadata["resources"][0]["licenses"][0]["name"] = "NOT-A-REAL-SPDX-LICENSE-TEST"
    result = validate_metadata(metadata)
    assert any(i["code"] == "spdx_unknown" and i["severity"] == "error" for i in result["issues"])
    assert result["mechanical_valid"] is False


def test_columns_nullability_and_units_are_evidence(tmp_path):
    prof = csv_profile(tmp_path)
    metadata = build_skeleton(prof)
    metadata["resources"][0]["schema"]["fields"][1]["nullable"] = False
    result = validate_metadata(metadata, profile=prof)
    codes = {i["code"] for i in result["issues"]}
    assert "observed_null_conflict" in codes
    assert "unit_column_evidence" in codes
    assert "unit_relationship_unresolved" in codes
    metadata["resources"][0]["schema"]["fields"].pop()
    assert any(i["code"] == "column_missing" for i in validate_metadata(metadata, profile=prof)["issues"])


def test_single_table_evidence_is_not_applied_to_all_resources(tmp_path):
    prof = csv_profile(tmp_path)
    metadata = build_skeleton(prof)
    metadata["resources"].append(copy.deepcopy(metadata["resources"][0]))
    result = validate_metadata(metadata, profile=prof)
    assert any(i["code"] == "resource_evidence_ambiguous" for i in result["issues"])
    assert not any(i["code"] == "unit_column_evidence" for i in result["issues"])


def test_collect_local_snapshots_and_no_implicit_url_reads(tmp_path, monkeypatch):
    source = tmp_path / "rows.csv"
    source.write_text("a\n0\n")
    metadata_path = tmp_path / "meta.json"
    metadata_path.write_text('{"resources":[],"url":"http://127.0.0.1/private"}')
    monkeypatch.setattr(collect, "safe_get_json", lambda *a, **k: pytest.fail("Local collection must not crawl metadata URLs"))
    result = collect.collect_inputs(data=source, metadata=metadata_path, output_dir=tmp_path / "run")
    assert len(result["snapshots"]) == 2
    assert result["snapshots"][0]["sha256"] == file_hash(metadata_path)
    assert result["profile"]["columns"]["a"]["min"] == 0
    assert (tmp_path / "run/collection.json").exists()


@pytest.mark.parametrize("count_response", [{"count": 3}, {"data": [[3]]}, 3])
def test_generation_collection_never_fetches_existing_metadata(tmp_path, monkeypatch, count_response):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if "/meta/" in url:
            pytest.fail("Generation leaked metadata")
        if "rowcount" in url:
            return count_response
        if "/rows/" in url:
            return [{"a": 0}, {"a": 1}]
        return {"name": "sample_table", "columns": {"a": {"data_type": "integer"}}}

    monkeypatch.setattr(collect, "safe_get_json", fake_get)
    monkeypatch.setattr(collect, "_public_https", urlsplit)
    result = collect.collect_inputs(table="sample_table", include_metadata=False, max_rows=2, output_dir=tmp_path / "run")
    assert result["metadata"] is None
    assert result["profile"]["row_count"] == 3
    assert result["profile"]["coverage"]["complete"] is False
    assert all(item["kind"] != "metadata" for item in result["snapshots"])
    assert len(calls) == 3


@pytest.mark.parametrize("table", ["data.foo", "foo/../../bar", "foo?limit=5", "foo;DELETE", "", "a" * 64])
def test_table_name_strict(table):
    with pytest.raises(WorkflowError):
        collect.validate_table_name(table)


@pytest.mark.parametrize("url", ["http://example.org", "https://127.0.0.1", "https://[::1]", "https://169.254.169.254", "https://user:secret@example.org", "https://example.org:8080"])
def test_public_get_rejects_private_or_credential_urls(url):
    with pytest.raises(WorkflowError):
        collect._public_https(url)


def test_ontology_index_is_frozen_and_checks_deprecated_ids(tmp_path):
    path = tmp_path / "tiny.ttl"
    path.write_text('''@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<http://openenergy-platform.org/ontology/oeo/OEO_00000001> a owl:Class ; rdfs:label "electric energy"@en .
<http://openenergy-platform.org/ontology/oeo/OEO_00000002> a owl:Class ; rdfs:label "old energy" ; owl:deprecated true .
''')
    index = ontology.build_index(path, tmp_path / "index.json", "test-fixture")
    assert ontology.lookup(index, "OEO:00000001")["labels"] == ["electric energy"]
    assert ontology.lookup(index, "OEO:99999999") is None
    assert ontology.lookup(index, "https://example.invalid/OEO_00000001") is None
    assert ontology.search(index, "electric energy")[0]["id"].endswith("00000001")
    metadata = build_skeleton(csv_profile(tmp_path))
    field = metadata["resources"][0]["schema"]["fields"][0]
    field["isAbout"] = [{"name": "old energy", "@id": "http://openenergy-platform.org/ontology/oeo/OEO_00000002"}]
    assert any(i["code"] == "ontology_deprecated" for i in validate_metadata(metadata, ontology_index=index)["issues"])
    field["isAbout"][0]["@id"] = "http://openenergy-platform.org/ontology/oeo/OEO_99999999"
    assert any(i["code"] == "ontology_unknown" for i in validate_metadata(metadata, ontology_index=index)["issues"])


@pytest.mark.parametrize("declared,database", [
    ("geometry(Point, 4326)", "geometry(Point, 4326)"),
    ("GEOMETRY ( Point,4326 )", "geometry(Point, 4326)"),
    ("geography(Point, 4326)", "geography(Point,4326)"),
    ("char", "char"),
    ("CHAR(2)", "character(2)"),
    ("character varying(120)", "varchar(120)"),
    ("timestamp(6) with time zone", "timestamp with time zone"),
    ("integer", "int4"),
    ("numeric(10, 2)", "numeric"),
])
def test_database_type_normalization_is_symmetric(tmp_path, declared, database):
    metadata = build_skeleton(csv_profile(tmp_path, text="value\n1\n"))
    metadata["resources"][0]["schema"]["fields"][0]["type"] = declared
    result = validate_metadata(metadata, db_schema={"columns": {"value": {"data_type": database}}})
    assert result["mechanical_valid"]
    assert not any(i["code"] == "database_type_conflict" for i in result["issues"])


@pytest.mark.parametrize("declared,database", [
    ("geometry(Point, 4326)", "geometry(Point,3857)"),
    ("geometry(Point, 4326)", "geometry(Polygon,4326)"),
    ("geometry(Point, 4326)", "geography(Point,4326)"),
    ("char", "integer"),
])
def test_type_normalization_preserves_real_database_conflicts(tmp_path, declared, database):
    metadata = build_skeleton(csv_profile(tmp_path, text="value\n1\n"))
    metadata["resources"][0]["schema"]["fields"][0]["type"] = declared
    result = validate_metadata(metadata, db_schema={"columns": {"value": {"data_type": database}}})
    assert not result["mechanical_valid"]
    assert any(i["code"] == "database_type_conflict" and i["severity"] == "error" for i in result["issues"])
