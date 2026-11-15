"""OEP metadata uploads: reviewable plans, explicit writes and readback.

Protocol follows the checked-out OEP API, not a claim of live deployment
compatibility. Credentials are read only when sending and never saved in plans.
"""

import copy
import difflib
import ipaddress
import json
import os
import re
from html.parser import HTMLParser
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from urllib.parse import quote, urlsplit, urljoin

import requests

from .common import WorkflowError, now, load_json, write_json, json_hash


def safe_base_url(value):
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise WorkflowError("Invalid OEP base URL") from None
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username or parsed.password or
            parsed.query or parsed.fragment or parsed.path not in ("", "/") or
            port not in (None, 443) or not host or host.endswith(".") or
            host in ("localhost", "localhost.localdomain") or
            host.endswith((".local", ".localhost", ".internal"))):
        raise WorkflowError("OEP base URL must be a public HTTPS origin without credentials")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host) or "." not in host:
            raise WorkflowError("Invalid public OEP hostname")
    else:
        if not address.is_global:
            raise WorkflowError("Private or local OEP hosts are not supported")
    return "https://" + host.lower()


def table_name(table):
    if not isinstance(table, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise WorkflowError("Expected an unqualified OEP table name")
    return table


def load_cookie_session(path, base_url="https://openenergyplatform.org"):
    """Load only an explicitly supplied Netscape cookie file; no browser access."""
    base = safe_base_url(base_url)
    jar = MozillaCookieJar(str(path))
    try:
        jar.load(ignore_discard=True, ignore_expires=False)
    except (OSError, ValueError):
        raise WorkflowError("Cannot load the explicitly supplied Netscape cookie file") from None
    host = urlsplit(base).hostname
    session = requests.Session()
    session.trust_env = False
    for cookie in jar:
        # Do not import unrelated account cookies or broad-domain credentials.
        if cookie.domain.lstrip(".").lower() == host and cookie.secure:
            session.cookies.set_cookie(cookie)
    if not any(c.name == "sessionid" for c in session.cookies):
        raise WorkflowError("Cookie file has no valid secure sessionid for the OEP origin")
    return session


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.text_parts = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text_parts.append(data)

    @property
    def text(self):
        return " ".join(" ".join(self.text_parts).split())


def review_status(html):
    """Fail closed for a detected ongoing OPR; report unfamiliar layouts."""
    page = Page(html)
    if ("Under review" in page.text or any(
            attrs.get("id") in ("opr-button-reviewer-continue", "opr-button-contributor-continue")
            for _, attrs in page.nodes)):
        return "active"
    if ("Not reviewed" in page.text or "Latest review completed" in page.text or
            any(attrs.get("id") == "opr-button-start" for _, attrs in page.nodes)):
        return "inactive"
    return "unverified"


def _plan_body(plan):
    return {key: val for key, val in plan.items() if key != "plan_hash"}


class UploadPlan(dict):
    """A serialized plan with a runtime-only directory binding."""

    def __init__(self, values, directory):
        super().__init__(values)
        self.directory = Path(directory).resolve()


def plan_directory(plan):
    if not isinstance(plan, UploadPlan):
        raise WorkflowError("Load the upload plan by filename to bind its directory")
    return plan.directory


def check_plan(plan, operation, expected_plan_hash=None):
    plan = UploadPlan(load_json(plan), Path(plan).resolve().parent) if isinstance(plan, (str, Path)) else copy.deepcopy(plan)
    if not isinstance(plan, dict) or plan.get("operation") != operation:
        raise WorkflowError("Wrong upload plan operation")
    digest = json_hash(_plan_body(plan))
    if digest != plan.get("plan_hash") or (expected_plan_hash and digest != expected_plan_hash):
        raise WorkflowError("Upload plan hash changed")
    return plan


def save_plan(out_dir, plan):
    plan["plan_hash"] = json_hash(_plan_body(plan))
    write_json(Path(out_dir) / "upload.plan.json", plan)
    return UploadPlan(plan, out_dir)


def claim_attempt(out_dir, plan_hash):
    """Exclusive marker prevents concurrent or uncertain duplicate writes."""
    try:
        with (Path(out_dir) / "upload.attempt.json").open("x", encoding="utf-8") as stream:
            json.dump({"started_at": now(), "plan_hash": plan_hash, "status": "started"}, stream)
    except FileExistsError:
        raise WorkflowError("This plan already attempted a write; inspect readback before preparing another plan") from None


class OEPClient:
    def __init__(self, base_url="https://openenergyplatform.org", session=None, timeout=30):
        self.base_url = safe_base_url(base_url)
        self.session = session if session is not None else requests.Session()
        if session is None:
            self.session.trust_env = False
        self.timeout = timeout

    def _url(self, path):
        url = urljoin(self.base_url + "/", path)
        if urlsplit(url).username or urlsplit(url).password:
            raise WorkflowError("Credentials in OEP request URL refused")
        if safe_base_url("https://" + (urlsplit(url).hostname or "")) != self.base_url:
            raise WorkflowError("Cross-origin OEP request refused")
        if urlsplit(url).scheme != "https" or urlsplit(url).port not in (None, 443):
            raise WorkflowError("Unsafe OEP request URL")
        return url

    def _request(self, method, path, **kwargs):
        try:
            response = self.session.request(method, self._url(path), timeout=self.timeout,
                                            allow_redirects=False, **kwargs)
        except requests.RequestException:
            message = "Write outcome uncertain; do not retry blindly" if method != "GET" else "OEP read failed"
            raise WorkflowError(message) from None
        if 300 <= response.status_code < 400:
            raise WorkflowError("OEP redirect refused; check origin or authenticated session")
        if response.status_code in (401, 403):
            raise WorkflowError("OEP authentication or permission denied")
        if not 200 <= response.status_code < 300:
            if method != "GET" and response.status_code >= 500:
                raise WorkflowError("Write outcome uncertain; server error; do not retry blindly")
            raise WorkflowError(f"OEP request refused (HTTP {response.status_code})")
        return response

    @staticmethod
    def _json(response, *, write=False):
        try:
            value = response.json()
        except (ValueError, TypeError):
            message = "Write outcome uncertain; malformed response; do not retry blindly" if write else "Malformed OEP JSON response"
            raise WorkflowError(message) from None
        if not isinstance(value, dict):
            raise WorkflowError("Write outcome uncertain; unexpected JSON shape" if write else "Unexpected OEP JSON shape")
        return value

    def read_metadata(self, table):
        value = self._json(self._request("GET", f"/api/v0/tables/{quote(table_name(table))}/meta/"))
        if not isinstance(value.get("resources"), list):
            raise WorkflowError("OEP response is not an OEMetadata document")
        return value

    def table_review_status(self, table):
        try:
            page = self._request("GET", f"/database/{quote(table_name(table))}")
        except WorkflowError:
            return "unverified"
        return review_status(page.text)

    def prepare_metadata_upload(self, metadata, table, out_dir):
        table = table_name(table)
        metadata = load_json(metadata) if isinstance(metadata, (str, Path)) else copy.deepcopy(metadata)
        if not isinstance(metadata, dict) or not isinstance(metadata.get("resources"), list):
            raise WorkflowError("Metadata upload needs an OEMetadata document")
        remote = self.read_metadata(table)
        status = self.table_review_status(table)
        out = Path(out_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)
        write_json(out / "metadata.remote.backup.json", remote)
        write_json(out / "metadata.upload.json", metadata)
        old = json.dumps(remote, ensure_ascii=False, sort_keys=True, indent=2).splitlines(True)
        new = json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2).splitlines(True)
        (out / "metadata.diff").write_text("".join(difflib.unified_diff(old, new, fromfile="remote", tofile="candidate")), encoding="utf-8")
        return save_plan(out, {
            "operation": "metadata-upload", "created_at": now(), "base_url": self.base_url,
            "table": table, "payload_hash": json_hash(metadata), "remote_hash": json_hash(remote),
            "review_status": status, "executable": status == "inactive", "out_dir": ".",
            "limitations": (["review_status_unverified"] if status == "unverified" else []) +
                           ["Client recheck is not atomic conditional-write protection"],
            "protocol": "OEP source-derived metadata API; live write unverified",
        })

    def execute_metadata_upload(self, plan, metadata, *, execute=False, token_env="OEP_API_TOKEN", expected_plan_hash=None):
        plan = check_plan(plan, "metadata-upload", expected_plan_hash)
        metadata = load_json(metadata) if isinstance(metadata, (str, Path)) else copy.deepcopy(metadata)
        if plan["base_url"] != self.base_url or json_hash(metadata) != plan["payload_hash"]:
            raise WorkflowError("Upload target or local metadata changed; prepare a new plan")
        if not execute:
            return {"status": "dry_run", "plan_hash": plan["plan_hash"]}
        out = plan_directory(plan)
        if (out / "upload.attempt.json").exists():
            raise WorkflowError("This plan already attempted a write; inspect readback before preparing another plan")
        if plan.get("review_status") == "active":
            raise WorkflowError("Active OPR freezes this metadata snapshot; upload blocked")
        # A valid old plan hash does not make an unverified review state safe.
        if not plan.get("executable") or plan.get("review_status") != "inactive":
            raise WorkflowError("OPR status is unverified in this plan; confirm inactivity and prepare a new plan")
        current_status = self.table_review_status(plan["table"])
        if current_status == "active":
            raise WorkflowError("Active OPR freezes this metadata snapshot; upload blocked")
        if current_status != "inactive":
            raise WorkflowError("OPR status is unverified at execution; upload blocked before any write")
        if json_hash(self.read_metadata(plan["table"])) != plan["remote_hash"]:
            raise WorkflowError("Remote metadata changed; prepare a new plan")
        token = os.environ.get(token_env)
        if not token or "\n" in token or "\r" in token:
            raise WorkflowError("Set the named API Token environment variable before execution")
        claim_attempt(out, plan["plan_hash"])
        try:
            response = self._request("POST", f"/api/v0/tables/{quote(plan['table'])}/meta/",
                                     json=metadata, headers={"Authorization": "Token " + token})
            stored = self._json(response, write=True)
            if not isinstance(stored.get("resources"), list):
                raise WorkflowError("Write outcome uncertain; response is not metadata")
            readback = self.read_metadata(plan["table"])
            write_json(out / "metadata.readback.json", readback)
            if json_hash(readback) != json_hash(stored):
                raise WorkflowError("Write outcome uncertain; response and readback differ")
            receipt = {"operation": "metadata-upload", "status": "verified" if json_hash(readback) == plan["payload_hash"] else "stored_with_server_changes",
                       "completed_at": now(), "plan_hash": plan["plan_hash"], "table": plan["table"],
                       "base_url": self.base_url, "requested_hash": plan["payload_hash"], "stored_hash": json_hash(readback),
                       "limitations": plan["limitations"]}
            write_json(out / "upload.receipt.json", receipt)
            return receipt
        except WorkflowError:
            write_json(out / "upload.receipt.json", {"operation": "metadata-upload", "status": "not_verified_do_not_retry", "plan_hash": plan["plan_hash"], "at": now()})
            raise
