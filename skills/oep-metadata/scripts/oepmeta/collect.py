"""Read-only evidence collection with local snapshots and public-HTTPS bounds."""

import ipaddress
import json
import re
import shutil
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import certifi
import urllib3

from .common import WorkflowError, file_hash, json_hash, load_json, now, write_json
from .profile import profile_data

MAX_RESPONSE_BYTES = 120 * 1024 * 1024
MAX_BACKGROUND_BYTES = 2 * 1024 * 1024
MAX_REMOTE_ROWS = 500000


def validate_table_name(table):
    if not isinstance(table, str) or not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", table):
        raise WorkflowError("OEP table must be a single lowercase PostgreSQL identifier (no schema, URL or SQL)")
    return table


def _public_https(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
        raise WorkflowError("Evidence URLs must be public HTTPS without credentials or custom ports")
    if parts.fragment:
        raise WorkflowError("URL fragments are not supported")
    try:
        addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise WorkflowError(f"Cannot resolve public host: {parts.hostname}") from exc
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise WorkflowError("Private, loopback, reserved and link-local evidence hosts are forbidden")
    return parts


def safe_get_json(url, *, max_bytes=MAX_RESPONSE_BYTES):
    """Bounded, unauthenticated public GET; redirects are rejected entirely.

    Connect to a validated public IP, retaining the original TLS hostname and
    Host header. This prevents a second DNS lookup from rebinding to a private
    address. No retries, redirects, imported credentials or proxy environment.
    """
    parts = _public_https(url)
    addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise WorkflowError("Evidence host changed to a private or reserved address")
    address = sorted(addresses, key=lambda item: item[0] != socket.AF_INET)[0][4][0]
    path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
    try:
        with urllib3.HTTPSConnectionPool(address, port=443, assert_hostname=parts.hostname, server_hostname=parts.hostname,
                                        cert_reqs="CERT_REQUIRED", ca_certs=certifi.where(), timeout=urllib3.Timeout(connect=10, read=90)) as pool:
            response = pool.urlopen("GET", path, headers={"Host": parts.hostname, "Accept": "application/json"},
                                    redirect=False, retries=False, preload_content=False)
            if 300 <= response.status < 400:
                raise WorkflowError("Redirects are not followed for evidence collection")
            if not 200 <= response.status < 300:
                raise WorkflowError(f"Evidence GET failed with HTTP {response.status}")
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise WorkflowError("Remote response exceeds the configured byte bound")
            raw = bytearray()
            for chunk in response.stream(amt=65536):
                raw.extend(chunk)
                if len(raw) > max_bytes:
                    raise WorkflowError("Remote response exceeds the configured byte bound")
            response.release_conn()
    except urllib3.exceptions.HTTPError as exc:
        raise WorkflowError(f"Public HTTPS evidence request failed: {type(exc).__name__}") from exc
    try:
        return json.loads(raw.decode("utf-8-sig"), parse_constant=lambda x: (_ for _ in ()).throw(WorkflowError(f"Invalid JSON number: {x}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowError("Remote evidence did not contain valid UTF-8 JSON") from exc


def collect_inputs(*, data=None, metadata=None, table=None, background=(), base_url="https://openenergyplatform.org", max_rows=None, output_dir=None, include_metadata=True):
    """Collect only explicitly requested sources; never crawl metadata links.

    Remote row reads default to 10,000 rows with a separate precise row count.
    Supply a larger positive max_rows (up to 500,000) when needed. Generation
    passes include_metadata=False to avoid leaking existing metadata answers.
    """
    if max_rows is not None and (isinstance(max_rows, bool) or not isinstance(max_rows, int) or max_rows < 1):
        raise WorkflowError("max_rows must be a positive integer")
    if not any((data, metadata, table, background)):
        raise WorkflowError("Provide metadata, data, an OEP table or background files")
    if not include_metadata and metadata is not None:
        raise WorkflowError("Generation evidence cannot include existing metadata")
    output_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="oep-evidence-"))
    snapshot_dir = output_dir / "inputs"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    result = {"metadata": None, "profile": None, "db_schema": None, "evidence": [], "snapshots": [], "collected_at": now(), "table": table, "base_url": base_url.rstrip("/")}

    def snapshot_local(source, label):
        source = Path(source).resolve(strict=True)
        if not source.is_file():
            raise WorkflowError("Evidence input must be a regular file")
        target = snapshot_dir / f"{label}{source.suffix.lower()}"
        if source != target.resolve():
            shutil.copyfile(source, target)
        item = {"kind": label, "source": f"inputs/{target.name}", "path": target.relative_to(output_dir).as_posix(), "sha256": file_hash(target), "bytes": target.stat().st_size}
        result["snapshots"].append(item)
        return target, item

    def remote(url, label):
        value = safe_get_json(url)
        path = snapshot_dir / f"{label}.json"
        write_json(path, value)
        item = {"kind": label, "source": url, "path": path.relative_to(output_dir).as_posix(), "sha256": file_hash(path), "content_sha256": json_hash(value), "bytes": path.stat().st_size}
        result["snapshots"].append(item)
        return value, path, item

    def evidence(kind, content, source):
        # IDs are content-addressed and independent of list order / run path.
        digest = json_hash({"kind": kind, "content": content, "source": source})[:16]
        result["evidence"].append({"id": f"ev-{digest}", "kind": kind, "content": content, "source": source})

    if metadata is not None:
        path, item = snapshot_local(metadata, "metadata")
        result["metadata"] = load_json(path)
        if not isinstance(result["metadata"], dict):
            raise WorkflowError("Metadata must be a JSON object")
        evidence("metadata", result["metadata"], item["source"])
    if data is not None:
        path, item = snapshot_local(data, "data")
        result["profile"] = profile_data(path, max_rows=max_rows)
        result["profile"]["source"] = item["source"]
        # The original filename may be used as a structural resource name.
        result["profile"]["original_filename"] = Path(data).name
        evidence("data_profile", result["profile"], item["source"])
    if table is not None:
        validate_table_name(table)
        base = base_url.rstrip("/")
        parts = _public_https(base)
        if parts.path not in ("", "/") or parts.query:
            raise WorkflowError("base_url must be an HTTPS origin")
        endpoint = f"{base}/api/v0/tables/{table}"
        schema, _, item = remote(endpoint + "/", "db_schema")
        result["db_schema"] = schema
        evidence("db_schema", schema, item["source"])
        if include_metadata and result["metadata"] is None:
            value, _, item = remote(endpoint + "/meta/", "metadata")
            if not isinstance(value, dict):
                raise WorkflowError("Remote metadata must be an object")
            result["metadata"] = value
            evidence("metadata", value, item["source"])
        if result["profile"] is None:
            if max_rows is not None and max_rows > MAX_REMOTE_ROWS:
                raise WorkflowError(f"Remote max_rows cannot exceed {MAX_REMOTE_ROWS}")
            count, _, count_item = remote(endpoint + "/rowcount?precise-below=1000000000", "rowcount")
            # Production OEP uses {"count": n}; tolerate the documented scalar.
            total = count.get("count") if isinstance(count, dict) else count
            if isinstance(count, dict) and "data" in count:
                cells = count["data"]
                if isinstance(cells, list) and len(cells) == 1 and isinstance(cells[0], list) and len(cells[0]) == 1:
                    total = cells[0][0]
            if isinstance(total, bool) or not isinstance(total, int) or total < 0:
                raise WorkflowError("Remote row count must be a nonnegative integer")
            limit = max_rows if max_rows is not None else 10000
            rows, path, item = remote(endpoint + f"/rows/?limit={limit}", "data")
            if not isinstance(rows, list) or len(rows) > limit:
                raise WorkflowError("Remote rows must be an array within the requested row limit")
            prof = profile_data(path)
            prof["source"] = item["source"]
            if len(rows) > total:
                raise WorkflowError("Rows and row count disagree; table may have changed during collection")
            complete = len(rows) == total
            prof["row_count"] = total
            prof["coverage"] = {"mode": "full" if complete else "server_prefix", "scanned_rows": len(rows), "total_rows": total,
                                "fraction": len(rows) / total if total else 1.0, "complete": complete,
                                "statistics_scope": "returned rows only", "order": "server default; not random",
                                "limitations": ["Row count and rows are separate requests, not a transactional snapshot."] + ([] if complete else ["Server prefix may miss categories, nulls, ranges and types."])}
            result["profile"] = prof
            evidence("rowcount", count, count_item["source"])
            evidence("data_profile", prof, item["source"])
    for index, source in enumerate(background):
        path, item = snapshot_local(source, f"background-{index:02}")
        if path.stat().st_size > MAX_BACKGROUND_BYTES:
            raise WorkflowError(f"Background text exceeds {MAX_BACKGROUND_BYTES} bytes; select a smaller document")
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise WorkflowError("Background files must be UTF-8 text (extract PDF/Office files first)") from exc
        evidence("background", content, item["source"])
    result["inputs_sha256"] = json_hash([{k: item[k] for k in ("kind", "source", "sha256")} for item in result["snapshots"]])
    write_json(output_dir / "collection.json", result)
    return result
