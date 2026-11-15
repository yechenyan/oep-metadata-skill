"""Deterministic, explicitly scoped CSV / JSON-row profiling.

Only empty CSV cells are treated as missing; strings such as NA, /, null and
0 are evidence, not configurable guesses about missing-value conventions.
"""

import csv
import json
import math
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from .common import WorkflowError, file_hash


def _kind(value, csv_input=False):
    if value is None or (csv_input and value == ""):
        return "null", None
    if isinstance(value, bool):
        return "boolean", value
    if isinstance(value, int):
        return "integer", value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise WorkflowError("Non-finite numeric values are not supported")
        return "number", value
    if isinstance(value, dict):
        return "object", value
    if isinstance(value, list):
        return "array", value
    if not isinstance(value, str):
        raise WorkflowError(f"Unsupported cell type {type(value).__name__}")
    # Do not lose significant leading zeros in identifiers.
    if csv_input and re.fullmatch(r"[+-]?(?:0|[1-9]\d*)", value):
        return "integer", int(value)
    if csv_input and re.fullmatch(r"[+-]?(?:\d+\.\d*|\d*\.\d+|\d+[eE][+-]?\d+|\d+\.\d*[eE][+-]?\d+)", value):
        number = float(value)
        if math.isfinite(number):
            return "number", number
    if csv_input and value.lower() in ("true", "false"):
        return "boolean", value.lower() == "true"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            date.fromisoformat(value)
            return "date", value
        except ValueError:
            pass
    if re.match(r"^\d{4}-\d{2}-\d{2}T", value):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return "datetime", value
        except ValueError:
            pass
    return "string", value


def _merged_type(kinds):
    kinds = set(kinds) - {"null"}
    if not kinds:
        return "unknown"
    if kinds <= {"integer", "number"}:
        return "number" if "number" in kinds else "integer"
    if len(kinds) == 1:
        return next(iter(kinds))
    return "string" if kinds <= {"string", "date", "datetime"} else "mixed"


def profile_data(path, max_rows=None, delimiter=None):
    """Profile all rows or an explicit prefix, counting total input rows.

    ``row_count`` is the number of input rows; ``scanned_rows`` and coverage
    distinguish the profiled prefix. Counts and ranges apply to that prefix.
    JSON inputs must be arrays of objects. Missing object keys count as null.
    """
    path = Path(path)
    if max_rows is not None and (isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows < 1):
        raise WorkflowError("max_rows must be a positive integer")
    if delimiter is not None and len(delimiter) != 1:
        raise WorkflowError("CSV delimiter must be one character")
    is_json = path.suffix.lower() == ".json"
    columns = []
    states = {}
    total = scanned = 0
    actual_delimiter = None

    def add_column(name):
        if not isinstance(name, str) or not name:
            raise WorkflowError("Column names must be nonempty strings")
        columns.append(name)
        states[name] = {"kinds": Counter(), "null_count": scanned, "values": Counter(), "decoded": {}, "minimum": None, "maximum": None}

    def consume(row):
        nonlocal total, scanned
        total += 1
        if not isinstance(row, dict):
            raise WorkflowError(f"Row {total} must be an object")
        # Include late columns even when outside the profiled prefix; their
        # values remain unknown and count as absent in the sampled prefix.
        for name in row:
            if name not in states:
                add_column(name)
        if max_rows is not None and scanned >= max_rows:
            return
        for name in columns:
            kind, value = _kind(row.get(name), csv_input=not is_json)
            state = states[name]
            state["kinds"][kind] += 1
            if kind == "null":
                state["null_count"] += 1
                continue
            # JSON type tags keep False, 0, "0" and other values distinct.
            key = kind + ":" + json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
            state["values"][key] += 1
            state["decoded"][key] = value
            if kind in ("integer", "number", "date", "datetime", "string"):
                # Range must not compare mixed numeric/string cells.
                old_min = state["minimum"]
                if old_min is None or type(old_min) is type(value) or (isinstance(old_min, (int, float)) and isinstance(value, (int, float))):
                    state["minimum"] = value if old_min is None else min(old_min, value)
                    state["maximum"] = value if state["maximum"] is None else max(state["maximum"], value)
        scanned += 1

    if is_json:
        try:
            rows = json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=lambda value: (_ for _ in ()).throw(WorkflowError(f"Invalid number {value}")))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise WorkflowError(f"Invalid UTF-8 JSON: {path}") from exc
        if not isinstance(rows, list):
            raise WorkflowError("JSON data must be an array of row objects")
        for row in rows:
            consume(row)
    else:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            sample = stream.read(65536)
            stream.seek(0)
            try:
                actual_delimiter = delimiter or csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            except csv.Error:
                actual_delimiter = delimiter or ("\t" if path.suffix.lower() == ".tsv" else ",")
            reader = csv.reader(stream, delimiter=actual_delimiter, strict=True)
            headers = next(reader, [])
            if len(headers) != len(set(headers)):
                raise WorkflowError("Duplicate CSV headers are ambiguous")
            for name in headers:
                add_column(name)
            try:
                for cells in reader:
                    if not cells:
                        continue
                    if len(cells) != len(headers):
                        raise WorkflowError(f"CSV row {reader.line_num} has {len(cells)} cells; expected {len(headers)}")
                    consume(dict(zip(headers, cells)))
            except csv.Error as exc:
                raise WorkflowError(f"Malformed CSV: {exc}") from exc

    result = {}
    for name in columns:
        state = states[name]
        inferred = _merged_type(state["kinds"])
        result[name] = {
            "type": inferred,
            "observed_types": dict(state["kinds"]),
            "null_count": state["null_count"],
            "non_null_count": scanned - state["null_count"],
            "nullable": bool(state["null_count"]),
            "distinct_count": len(state["values"]),
            "top_values": [{"value": state["decoded"][key], "count": count} for key, count in state["values"].most_common(10)],
            "min": None if inferred in ("unknown", "mixed", "boolean", "object", "array") else state["minimum"],
            "max": None if inferred in ("unknown", "mixed", "boolean", "object", "array") else state["maximum"],
        }
    return {
        "source": path.name, "source_sha256": file_hash(path),
        "format": "json" if is_json else "csv", "encoding": "UTF-8",
        "delimiter": actual_delimiter, "row_count": total, "scanned_rows": scanned,
        "coverage": {"mode": "full" if scanned == total else "prefix", "scanned_rows": scanned,
                     "total_rows": total, "fraction": scanned / total if total else 1.0,
                     "complete": scanned == total, "statistics_scope": "scanned rows only",
                     "limitations": [] if scanned == total else ["Prefix sample may miss later categories, ranges, nulls and types."]},
        "columns": result,
    }
