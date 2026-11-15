"""Shared IO, JSON pointers and hashes. No network or model calls."""

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]


class WorkflowError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return str(path)


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def escape(token):
    return str(token).replace("~", "~0").replace("/", "~1")


def parts(pointer):
    if pointer == "":
        return []
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise WorkflowError("Expected an absolute JSON Pointer")
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/")]


def get_pointer(document, pointer):
    current = document
    try:
        for part in parts(pointer):
            if isinstance(current, list):
                if not part.isdigit() or (len(part) > 1 and part.startswith("0")):
                    raise WorkflowError("Array index must be a canonical nonnegative integer")
                current = current[int(part)]
            else:
                current = current[part]
        return current
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise WorkflowError(f"Missing JSON Pointer: {pointer}") from exc


def set_pointer(document, pointer, value, *, remove=False):
    tokens = parts(pointer)
    if not tokens:
        raise WorkflowError("Root replacement is not supported")
    parent = get_pointer(document, "/" + "/".join(escape(p) for p in tokens[:-1])) if len(tokens) > 1 else document
    key = int(tokens[-1]) if isinstance(parent, list) else tokens[-1]
    if remove:
        del parent[key]
    else:
        parent[key] = copy.deepcopy(value)


def leaves(value, pointer=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, pointer + "/" + escape(key))
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from leaves(child, pointer + "/" + str(index))
    else:
        yield pointer, value


def empty(value):
    return value is None or value == "" or value == [] or value == {} or (isinstance(value, str) and value.strip() in ("", "None", "null", "[]", "{}"))
