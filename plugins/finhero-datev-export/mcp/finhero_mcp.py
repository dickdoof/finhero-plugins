#!/usr/bin/env python3
"""finHero MCP server for the finhero-datev-export plugin. Standard library only.

Speaks MCP (JSON-RPC 2.0, newline-delimited) over stdin/stdout. The finHero API token comes
from the plugin's sensitive userConfig option `api_token`, which Claude Code passes in as
FINHERO_API_TOKEN (see ../.mcp.json). Nothing is read from the user's files.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("FINHERO_BASE_URL", "https://fin-hero.de").rstrip("/")
API_PAGE = "https://fin-hero.de/dashboard/api/"
SETTINGS_PAGE = "https://fin-hero.de/dashboard/settings/"
USER_AGENT = "finhero-claude-plugin/1.3.0"
PROTOCOL_VERSION = "2025-06-18"
PROVIDERS = ["STRIPE", "ADYEN", "MOLLIE", "PADDLE", "LEMONSQUEEZY", "PAYPAL"]
FORMATS = ["DATEV", "BMD", "BEXIO", "ABACUS"]
DONE, FAILED = "COMPLETED", "ERROR"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ApiError(Exception):
    pass


def token():
    value = os.environ.get("FINHERO_API_TOKEN", "").strip()
    # An unset userConfig value can arrive as the literal placeholder.
    if not value or value.startswith("${"):
        raise ApiError(f"No finHero API token configured. Create one at {API_PAGE}, then run /plugin, "
                       "open finhero-datev-export and choose 'Configure options' to enter it.")
    return value


def request(method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers={
        "Authorization": f"Bearer {token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            payload = res.read()
            return (payload, res.headers) if raw else json.loads(payload or b"null")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read())
            message = payload.get("error") or payload.get("reason") or e.reason
        except Exception:
            message = e.reason
        if e.code in (401, 403):
            message = f"{message}. Check or recreate the token at {API_PAGE} and update it via /plugin."
        raise ApiError(f"HTTP {e.code}: {message}")
    except urllib.error.URLError as e:
        raise ApiError(f"Cannot reach {BASE_URL}: {e.reason}. Allow network access to fin-hero.de.")


def rows(result):
    # Export endpoints return the Supabase result shape {"data": [...], "error": ...}.
    if isinstance(result, dict):
        if result.get("error"):
            raise ApiError(str(result["error"]))
        return result.get("data") or []
    return result or []


def summarize(row):
    keys = ["id", "status", "start_date", "end_date", "payment_provider", "export_format",
            "transaction_count", "file_name", "error_message", "created_on"]
    return {k: row.get(k) for k in keys if k in row}


def get_export(export_id):
    found = rows(request("GET", f"/api/v1/data?id={urllib.parse.quote(str(export_id))}"))
    if not found:
        raise ApiError(f"Export {export_id} not found")
    return found[0]


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "finhero-export.zip"


# --- tools -----------------------------------------------------------------------------------

def tool_check(_):
    latest = rows(request("GET", "/api/v1/data?limit=1"))
    return {"ok": True, "latest_export": summarize(latest[0]) if latest else None}


def tool_list_exports(args):
    limit = max(1, min(int(args.get("limit") or 10), 100))
    return {"exports": [summarize(r) for r in rows(request("GET", f"/api/v1/data?limit={limit}"))]}


def tool_create_export(args):
    start, end = args.get("start_date", ""), args.get("end_date", "")
    if not DATE_RE.match(start) or not DATE_RE.match(end) or start > end:
        raise ApiError("start_date and end_date must be YYYY-MM-DD with start_date <= end_date")
    provider = str(args.get("provider") or "STRIPE").upper()
    fmt = str(args.get("format") or "DATEV").upper()
    if provider not in PROVIDERS:
        raise ApiError("provider must be one of " + ", ".join(PROVIDERS))
    if fmt not in FORMATS:
        raise ApiError("format must be one of " + ", ".join(FORMATS))
    created = rows(request("POST", "/api/v1/data/export", {
        "startDate": start, "endDate": end, "provider": provider, "format": fmt,
    }))
    if not created:
        raise ApiError("Export was not created")
    return summarize(created[0])


def tool_wait_for_export(args):
    # Bounded so a single tool call never runs into the client's timeout; call again if needed.
    deadline = time.time() + max(10, min(int(args.get("max_seconds") or 240), 300))
    delay = 5
    while True:
        row = get_export(args["export_id"])
        if row.get("status") in (DONE, FAILED) or time.time() >= deadline:
            result = summarize(row)
            result["finished"] = row.get("status") in (DONE, FAILED)
            return result
        time.sleep(delay)
        delay = min(delay * 1.5, 30)


def tool_download_export(args):
    export_id = args["export_id"]
    payload, headers = request("GET", f"/api/v1/data/file?exportId={urllib.parse.quote(str(export_id))}", raw=True)
    match = re.search(r'filename="?([^";]+)"?', headers.get("Content-Disposition", ""))
    name = safe_name(match.group(1) if match else f"finhero-export-{export_id}.zip")
    target = Path(args.get("directory") or "finhero-exports").expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    path = target / name
    path.write_bytes(payload)
    return {"path": str(path), "bytes": len(payload)}


def tool_setup_status(args):
    return request("GET", "/api/v1/setup" + ("?validate=1" if args.get("validate") else ""))


def tool_set_accounts(args):
    system = str(args.get("system") or "DATEV").upper()
    if system not in FORMATS:
        raise ApiError("system must be one of " + ", ".join(FORMATS))
    accounts = args.get("accounts")
    if not isinstance(accounts, dict) or not accounts:
        raise ApiError("accounts must be an object of field -> value")
    return request("PUT", "/api/v1/setup/accounting", {
        "system": system,
        # Keep leading zeros: everything is sent as text, the API normalizes.
        "accounts": {k: (None if v is None else str(v)) for k, v in accounts.items()},
        "activate": bool(args.get("activate")),
    })


DATE = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}
TOOLS = {
    "check": (tool_check, "Verify the finHero API token with a read-only call and return the latest export.",
              {"type": "object", "properties": {}}),
    "list_exports": (tool_list_exports, "List the customer's finHero exports, newest first.",
                     {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}}}),
    "create_export": (tool_create_export,
                      "Order a finHero export (DATEV Buchungsstapel, BMD, bexio or Abacus) for an inclusive date range. "
                      "Returns the export with status PENDING; then use wait_for_export and download_export.",
                      {"type": "object", "required": ["start_date", "end_date"], "properties": {
                          "start_date": DATE, "end_date": DATE,
                          "provider": {"type": "string", "enum": PROVIDERS, "default": "STRIPE"},
                          "format": {"type": "string", "enum": FORMATS, "default": "DATEV"}}}),
    "wait_for_export": (tool_wait_for_export,
                        "Poll an export until it is COMPLETED or ERROR, at most max_seconds (default 240). "
                        "If finished is false, call again.",
                        {"type": "object", "required": ["export_id"], "properties": {
                            "export_id": {"type": ["string", "integer"]},
                            "max_seconds": {"type": "integer", "minimum": 10, "maximum": 300}}}),
    "download_export": (tool_download_export, "Download the ZIP of a finished export into a local directory.",
                        {"type": "object", "required": ["export_id"], "properties": {
                            "export_id": {"type": ["string", "integer"]},
                            "directory": {"type": "string", "description": "Target directory, default ./finhero-exports"}}}),
    "setup_status": (tool_setup_status,
                     "Show finHero setup: connected payment providers (never the keys), account settings per "
                     "accounting system and the steps still missing. validate=true also checks provider keys.",
                     {"type": "object", "properties": {"validate": {"type": "boolean"}}}),
    "set_accounts": (tool_set_accounts,
                     "Save account settings for one accounting system, e.g. DATEV consultant_no, client_no, "
                     "debitor_account_no, fee_account_no. Only known fields, digits only.",
                     {"type": "object", "required": ["system", "accounts"], "properties": {
                         "system": {"type": "string", "enum": FORMATS},
                         "accounts": {"type": "object", "additionalProperties": {"type": ["string", "integer", "null"]}},
                         "activate": {"type": "boolean", "description": "Switch the system on for the monthly auto-export"}}}),
}


# --- MCP plumbing ----------------------------------------------------------------------------

def handle(msg):
    method, msg_id = msg.get("method"), msg.get("id")
    if msg_id is None:  # notification
        return None
    if method == "initialize":
        result = {"protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL_VERSION),
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "finhero", "version": "1.3.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (_, d, s) in TOOLS.items()]}
    elif method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": f"Unknown tool {name}"}}
        try:
            data = TOOLS[name][0](params.get("arguments") or {})
            result = {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}]}
        except (ApiError, KeyError, ValueError) as e:
            text = str(e) if isinstance(e, ApiError) else f"Invalid arguments: {e}"
            result = {"content": [{"type": "text", "text": text}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            reply = handle(json.loads(line))
        except Exception as e:  # never let one bad message kill the server
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
