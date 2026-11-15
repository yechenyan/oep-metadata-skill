"""Pinned OEMetadata validation plus independent evidence checks.

Passing these mechanical checks never establishes semantic correctness,
licensing authority, or suitability of an ontology term.
"""

import copy
import re
from importlib.metadata import version

from jsonschema import Draft202012Validator, FormatChecker

from .common import SKILL_ROOT, WorkflowError, empty, escape, json_hash, leaves, load_json, parts

VERSION = "OEMetadata-2.0.4"
ASSETS = SKILL_ROOT / "assets" / "oemetadata-2.0.4"


def schema_fragment(pointer):
    """Resolve an instance pointer against the pinned, inline metadata schema."""
    current = load_json(ASSETS / "schema.json")
    for token in parts(pointer):
        properties = current.get("properties", {})
        if token in properties:
            current = properties[token]
        elif token.isdecimal() and isinstance(current.get("items"), dict):
            current = current["items"]
        else:
            raise WorkflowError("No schema field at this metadata pointer: " + pointer)
    return {"ok": True, "pointer": pointer, "target_version": VERSION, "schema": current,
            "scope": "Schema specification only; example values are not dataset evidence."}


def _types_compatible(declared, observed):
    declared = _canonical_type(declared)
    observed = _canonical_type(observed)
    return declared == observed or (declared == "number" and observed == "integer") or (declared == "string" and observed in ("date", "datetime"))


def profile_payload(value):
    """Accept a profile or its CLI response; reject accidental empty templates."""
    if isinstance(value, dict) and "columns" not in value and "profile" in value:
        value = value["profile"]
    if not isinstance(value, dict) or not isinstance(value.get("columns"), dict):
        raise WorkflowError("Expected a data profile with a columns object, or a profile command response")
    if any(not isinstance(name, str) or not isinstance(stats, dict) or not isinstance(stats.get("type"), str)
           for name, stats in value["columns"].items()):
        raise WorkflowError("Profile columns require string names and typed statistics objects")
    return value


def validate_metadata(metadata, profile=None, db_schema=None, ontology_index=None):
    if profile is not None:
        profile = profile_payload(profile)
    schema = load_json(ASSETS / "schema.json")
    issues = []
    checker = FormatChecker()
    required_formats = {value for pointer, value in leaves(schema) if pointer.endswith("/format") and isinstance(value, str)}
    missing_formats = required_formats - set(checker.checkers)
    if missing_formats:
        raise WorkflowError(f"Missing JSON Schema format checkers: {sorted(missing_formats)}. Install pinned jsonschema[format-nongpl] dependencies.")

    def issue(pointer, code, severity, message):
        issues.append({"pointer": pointer, "code": code, "severity": severity, "message": message})

    structural = list(Draft202012Validator(schema).iter_errors(metadata))
    formatted = list(Draft202012Validator(schema, format_checker=checker).iter_errors(metadata))
    format_errors = [error for error in formatted if error.validator == "format"]
    for error in structural:
        pointer = "".join("/" + escape(part) for part in error.absolute_path)
        issue(pointer, "schema_" + str(error.validator), "error", error.message)
    for error in format_errors:
        pointer = "".join("/" + escape(part) for part in error.absolute_path)
        issue(pointer, "format_" + str(error.validator_value), "error", error.message)
    if not isinstance(metadata, dict):
        return {"schema_valid": False, "format_valid": False, "issues": issues, "metadata_version": None, "target_version": VERSION}
    actual_version = metadata.get("metaMetadata", {}).get("metadataVersion") if isinstance(metadata.get("metaMetadata"), dict) else None
    if actual_version != VERSION:
        issue("/metaMetadata/metadataVersion", "metadata_version", "error", f"Expected {VERSION}; found {actual_version!r}. Convert explicitly before processing.")

    license_doc = load_json(SKILL_ROOT / "assets" / "spdx" / "licenses.json")
    licenses = {item["licenseId"]: item for item in license_doc["licenses"]}
    for pointer, value in leaves(metadata):
        if isinstance(value, str) and re.search(r"\b(?:todo|tbd|fixme|placeholder)\b|<[^>]*>", value, re.I):
            issue(pointer, "placeholder", "warning", "Contains a placeholder; supply evidence or retain as an explicit unknown.")
        if pointer.endswith("/name") and ("/licenses/" in pointer.lower() or "/sourcelicenses/" in pointer.lower() or "/metadataLicense/" in pointer):
            if empty(value):
                issue(pointer, "license_unknown", "warning", "License identifier is unknown; no licensing authority is inferred.")
            elif isinstance(value, str) and value.startswith("LicenseRef-"):
                issue(pointer, "license_custom", "warning", "Custom license reference requires its own license text and provenance.")
            elif not isinstance(value, str) or value not in licenses:
                issue(pointer, "spdx_unknown", "error", f"Identifier is absent from frozen SPDX {license_doc['licenseListVersion']}: {value!r}. Custom licenses need explicit handling.")
            elif licenses[value].get("isDeprecatedLicenseId"):
                issue(pointer, "spdx_deprecated", "warning", f"SPDX identifier {value!r} is deprecated.")
        if pointer.endswith("/@id") and isinstance(value, str) and re.search(r"OEO[_:]\d+", value):
            if ontology_index is None:
                issue(pointer, "ontology_not_checked", "warning", "OEO ID has not been checked against a frozen ontology index.")
            else:
                from .ontology import lookup
                record = lookup(ontology_index, value)
                if record is None:
                    issue(pointer, "ontology_unknown", "error", f"OEO identifier is absent from the frozen index: {value}")
                elif record.get("deprecated"):
                    issue(pointer, "ontology_deprecated", "error", "The selected ontology term is deprecated.")
                else:
                    from .common import get_pointer
                    try:
                        label = get_pointer(metadata, pointer.rsplit("/", 1)[0] + "/name")
                    except WorkflowError:
                        label = None
                    known_labels = record.get("labels", []) + record.get("synonyms", [])
                    if label and str(label).casefold() not in {item.casefold() for item in known_labels}:
                        issue(pointer.rsplit("/", 1)[0] + "/name", "ontology_label_mismatch", "warning", f"Label differs from frozen labels: {record.get('labels', [])}")

    resources = metadata.get("resources", [])
    if not isinstance(resources, list):
        resources = []
    database_columns = db_schema.get("columns", {}) if isinstance(db_schema, dict) else {}
    if isinstance(database_columns, list):
        database_columns = {item["name"]: item for item in database_columns if isinstance(item, dict) and "name" in item}
    if (profile or database_columns) and len(resources) != 1:
        issue("/resources", "resource_evidence_ambiguous", "warning", "Single-table evidence cannot be silently applied to multiple resources; select the target resource.")
    for ri, resource in enumerate(resources):
        if not isinstance(resource, dict):
            continue
        prefix = f"/resources/{ri}"
        fields = resource.get("schema", {}).get("fields", []) if isinstance(resource.get("schema"), dict) else []
        if not isinstance(fields, list):
            continue
        names = [f.get("name") for f in fields if isinstance(f, dict) and (f.get("name") is None or isinstance(f.get("name"), str))]
        if len(names) != len(set(str(name) for name in names)):
            issue(prefix + "/schema/fields", "duplicate_field", "error", "Metadata contains duplicate field names.")
        if len(resources) != 1:
            continue
        observed = profile.get("columns", {}) if profile else {}
        expected_names = set(database_columns or observed)
        if expected_names:
            for missing in sorted(expected_names - set(names)):
                issue(prefix + "/schema/fields", "column_missing", "error", f"Data column {missing!r} is absent from metadata.")
            for extra in sorted(set(name for name in names if isinstance(name, str)) - expected_names):
                issue(prefix + "/schema/fields", "column_extra", "error", f"Metadata column {extra!r} is absent from data/schema.")
        unit_columns = [name for name in observed if re.search(r"(?:^|_)units?(?:$|_)", name, re.I)]
        for name in unit_columns:
            values = observed[name].get("top_values", [])
            issue(prefix + "/schema/fields", "unit_column_evidence", "info", f"Column {name!r} contains potential row-dependent units (observed values: {values}); determine applicability from evidence, do not infer one global unit.")
        for fi, field in enumerate(fields):
            if not isinstance(field, dict):
                continue
            name = field.get("name")
            if not isinstance(name, str):
                continue
            fp = f"{prefix}/schema/fields/{fi}"
            if empty(field.get("description")):
                issue(fp + "/description", "description_unknown", "warning", "Field description is missing; semantic evidence is required.")
            if name in observed:
                stats = observed[name]
                if stats.get("type") not in ("unknown", "mixed") and field.get("type") and not _types_compatible(field["type"], stats["type"]):
                    issue(fp + "/type", "observed_type_conflict", "warning", f"Declared type {field['type']!r} differs from observed {stats['type']!r}; sample inference is not authoritative database typing.")
                if stats.get("null_count", 0) > 0 and field.get("nullable") is False:
                    issue(fp + "/nullable", "observed_null_conflict", "error", "Observed nulls conflict with nullable=false.")
                if unit_columns and stats.get("type") in ("number", "integer") and empty(field.get("unit")):
                    issue(fp + "/unit", "unit_relationship_unresolved", "warning", "Numeric column has no unit while potential unit columns exist; AI must establish the relationship from evidence.")
            if name in database_columns:
                column = database_columns[name]
                dtype = column.get("data_type", column.get("type"))
                if dtype and field.get("type") and not _types_compatible(field["type"], _canonical_type(dtype)):
                    issue(fp + "/type", "database_type_conflict", "error", f"Declared type differs from database type {dtype!r}.")
                nullable = column.get("is_nullable", column.get("nullable"))
                if isinstance(nullable, str) and nullable.upper() in ("YES", "NO"):
                    nullable = nullable.upper() == "YES"
                if isinstance(nullable, bool) and isinstance(field.get("nullable"), bool) and nullable != field["nullable"]:
                    issue(fp + "/nullable", "database_nullable_conflict", "error", "Metadata nullability differs from database constraint.")
    if profile and not profile.get("coverage", {}).get("complete", False):
        issue("/resources", "partial_data_coverage", "warning", "Data profile covers a non-random subset. Unobserved nulls, categories and ranges remain unknown.")
    return {"schema_valid": not structural and actual_version == VERSION, "format_valid": not format_errors,
            "mechanical_valid": not any(item["severity"] == "error" for item in issues),
            "issues": issues, "metadata_version": actual_version, "target_version": VERSION,
            "schema_sha256": json_hash(schema), "spdx_version": license_doc["licenseListVersion"],
            "formats_checked": sorted(required_formats),
            "scope": "Mechanical validation only; semantic correctness and license authority remain review tasks."}


def _canonical_type(dtype):
    value = str(dtype or "").lower().strip()
    if re.match(r"^(geometry|geography)\s*(?:\(|$)", value):
        # Shape and CRS parameters are part of a declared spatial type.
        return re.sub(r"\s+", "", value)
    value = re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", value)).strip()
    aliases = {"int": "integer", "int4": "integer", "int8": "integer", "bigint": "integer", "smallint": "integer",
               "float": "number", "double precision": "number", "real": "number", "numeric": "number", "decimal": "number",
               "text": "string", "varchar": "string", "character varying": "string", "char": "string", "character": "string",
               "bool": "boolean", "timestamp": "datetime", "timestamp without time zone": "datetime", "timestamp with time zone": "datetime"}
    return aliases.get(value, value)


def build_skeleton(profile, table_name=None, table_url=None):
    """Use OMI's published 1.1.0 specification interface, then clear guesses.

    Empty strings become null, example array entries are removed and template
    geographic zeros, false embargo and CC0 licensing are not inherited as
    dataset facts. Only metadataVersion and observed structural values remain.
    """
    profile = profile_payload(profile)
    if version("omi") != "1.1.0" or version("oemetadata") != "2.0.4":
        raise WorkflowError("Skeleton creation requires pinned omi==1.1.0 and oemetadata==2.0.4")
    from omi.base import get_metadata_specification
    specification = get_metadata_specification("OEMetadata-2.0")
    template = specification.template
    if json_hash(template) != json_hash(load_json(ASSETS / "template.json")):
        raise WorkflowError("Installed OMI template differs from the pinned template")

    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return []
        return None

    metadata = clean(copy.deepcopy(template))
    metadata["metaMetadata"]["metadataVersion"] = VERSION
    metadata["metaMetadata"]["metadataLicense"] = {"name": None, "title": None, "path": None}
    resource = clean(template["resources"][0])
    # Nullable strings support explicit unknowns; non-nullable nested objects
    # are retained, but remove unobserved fixed-size bounding boxes altogether.
    resource["spatial"]["extent"].pop("boundingBox", None)
    resource["embargoPeriod"]["isActive"] = None
    resource["type"] = "table"
    resource["format"] = profile.get("format")
    resource["encoding"] = profile.get("encoding")
    resource["schema"]["primaryKey"] = []
    resource["schema"]["foreignKeys"] = []
    resource["name"] = table_name
    metadata["name"] = table_name
    resource["path"] = table_url
    if profile.get("delimiter"):
        resource["dialect"]["delimiter"] = profile["delimiter"]
    fields = []
    for name, stats in profile.get("columns", {}).items():
        field = clean(template["resources"][0]["schema"]["fields"][0])
        field.update({"name": name, "type": None if stats["type"] in ("unknown", "mixed") else stats["type"],
                      "nullable": True if stats.get("null_count", 0) else None})
        fields.append(field)
    resource["schema"]["fields"] = fields
    metadata["resources"] = [resource]
    return metadata
