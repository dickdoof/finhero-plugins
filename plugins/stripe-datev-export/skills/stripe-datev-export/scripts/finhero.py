#!/usr/bin/env python3
"""finHero API client for the stripe-datev-export plugin. Standard library only.

Token: FINHERO_API_KEY env var, or the first line of ~/.config/finhero/token.
Create one at https://fin-hero.de/dashboard/api/

  finhero.py check
  finhero.py list [--limit N]
  finhero.py create --start YYYY-MM-DD --end YYYY-MM-DD [--provider STRIPE] [--format DATEV] [--wait] [--out DIR]
  finhero.py status EXPORT_ID
  finhero.py wait EXPORT_ID [--timeout SECONDS]
  finhero.py download EXPORT_ID [--out DIR]
  finhero.py setup-status [--validate]
  finhero.py set-provider-key --provider STRIPE [--secondary-id ID]   (key from stdin or FINHERO_PROVIDER_KEY)
  finhero.py set-accounts --system DATEV [--activate] field=value [field=value ...]

Every command prints one JSON object on stdout. Exit code 0 = ok, 1 = API/usage error,
2 = missing or invalid token, 3 = export failed or timed out.
"""
import argparse
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
TOKEN_FILE = Path.home() / ".config" / "finhero" / "token"
SETTINGS_URL = "https://fin-hero.de/dashboard/api/"
USER_AGENT = "finhero-claude-plugin/2026.10.0"
PROVIDERS = ["STRIPE", "ADYEN", "MOLLIE", "PADDLE", "LEMONSQUEEZY", "PAYPAL"]
FORMATS = ["DATEV", "BMD", "BEXIO", "ABACUS"]
DONE, FAILED = "COMPLETED", "ERROR"


class ApiError(Exception):
    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.exit(code)


def token():
    value = os.environ.get("FINHERO_API_KEY", "").strip()
    if not value and TOKEN_FILE.exists():
        value = (TOKEN_FILE.read_text().strip().splitlines() or [""])[0].strip()
    if not value:
        raise ApiError(f"No finHero API token. Create one at {SETTINGS_URL} and set FINHERO_API_KEY "
                       f"or save it to {TOKEN_FILE}.", 2)
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
            if raw:
                return payload, res.headers
            return json.loads(payload or b"null")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read())
            message = payload.get("error") or payload.get("reason") or e.reason
        except Exception:
            message = e.reason
        code = 2 if e.code in (401, 403) else 1
        if code == 2:
            message = f"{message}. Check or recreate your token at {SETTINGS_URL}"
        raise ApiError(f"HTTP {e.code}: {message}", code)
    except urllib.error.URLError as e:
        raise ApiError(f"Cannot reach {BASE_URL}: {e.reason}. If you run in a sandbox, allow network access to fin-hero.de.")


def rows(result):
    # The API returns the Supabase result shape {"data": [...], "error": ...}.
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


def wait_for(export_id, timeout):
    deadline = time.time() + timeout
    delay = 5
    while True:
        row = get_export(export_id)
        if row.get("status") in (DONE, FAILED):
            return row
        if time.time() >= deadline:
            raise ApiError(f"Export {export_id} still {row.get('status')} after {timeout}s. "
                           f"Run `finhero.py wait {export_id}` again later.", 3)
        time.sleep(delay)
        delay = min(delay * 1.5, 30)


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "finhero-export.zip"


def download(export_id, out_dir):
    payload, headers = request("GET", f"/api/v1/data/file?exportId={urllib.parse.quote(str(export_id))}", raw=True)
    match = re.search(r'filename="?([^";]+)"?', headers.get("Content-Disposition", ""))
    name = safe_name(match.group(1) if match else f"finhero-export-{export_id}.zip")
    target = Path(out_dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    path = target / name
    path.write_bytes(payload)
    return {"path": str(path), "bytes": len(payload)}


def read_provider_key():
    # Never take the key as an argument: it would end up in shell history and the transcript.
    value = os.environ.get("FINHERO_PROVIDER_KEY", "").strip()
    if not value and not sys.stdin.isatty():
        value = sys.stdin.read().strip()
    if not value:
        raise ApiError("No provider key. Pipe it in (e.g. `pbpaste | finhero.py set-provider-key ...`) "
                       "or set FINHERO_PROVIDER_KEY.")
    return value


def parse_assignments(pairs):
    accounts = {}
    for pair in pairs:
        if "=" not in pair:
            raise ApiError(f"Expected field=value, got {pair!r}")
        name, value = pair.split("=", 1)
        accounts[name.strip()] = value.strip()
    return accounts


def valid_date(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise argparse.ArgumentTypeError("use YYYY-MM-DD")
    return value


def main():
    p = argparse.ArgumentParser(description="finHero export API client")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    ls = sub.add_parser("list")
    ls.add_argument("--limit", type=int, default=10)
    cr = sub.add_parser("create")
    cr.add_argument("--start", required=True, type=valid_date)
    cr.add_argument("--end", required=True, type=valid_date)
    cr.add_argument("--provider", default="STRIPE", type=str.upper, choices=PROVIDERS)
    cr.add_argument("--format", default="DATEV", type=str.upper, choices=FORMATS)
    cr.add_argument("--wait", action="store_true", help="poll until done and download the file")
    cr.add_argument("--timeout", type=int, default=900)
    cr.add_argument("--out", default="finhero-exports")
    st = sub.add_parser("status")
    st.add_argument("id")
    wt = sub.add_parser("wait")
    wt.add_argument("id")
    wt.add_argument("--timeout", type=int, default=900)
    dl = sub.add_parser("download")
    dl.add_argument("id")
    dl.add_argument("--out", default="finhero-exports")
    ss = sub.add_parser("setup-status")
    ss.add_argument("--validate", action="store_true", help="also check stored provider keys")
    pk = sub.add_parser("set-provider-key")
    pk.add_argument("--provider", default="STRIPE", type=str.upper, choices=PROVIDERS)
    pk.add_argument("--secondary-id", help="PayPal Client-ID or Adyen balance account")
    sa = sub.add_parser("set-accounts")
    sa.add_argument("--system", default="DATEV", type=str.upper, choices=FORMATS)
    sa.add_argument("--activate", action="store_true", help="switch the system on for the monthly auto-export")
    sa.add_argument("fields", nargs="+", metavar="field=value")
    a = p.parse_args()

    try:
        if a.cmd == "check":
            latest = rows(request("GET", "/api/v1/data?limit=1"))
            out({"ok": True, "base_url": BASE_URL, "latest_export": summarize(latest[0]) if latest else None})
        if a.cmd == "list":
            out({"exports": [summarize(r) for r in rows(request("GET", f"/api/v1/data?limit={max(1, a.limit)}"))]})
        if a.cmd == "setup-status":
            out(request("GET", "/api/v1/setup" + ("?validate=1" if a.validate else "")))
        if a.cmd == "set-provider-key":
            body = {"provider": a.provider, "api_key": read_provider_key()}
            if a.secondary_id:
                body["secondary_id"] = a.secondary_id
            out(request("PUT", "/api/v1/setup/provider", body))
        if a.cmd == "set-accounts":
            out(request("PUT", "/api/v1/setup/accounting", {
                "system": a.system, "accounts": parse_assignments(a.fields), "activate": a.activate,
            }))
        if a.cmd == "status":
            out(summarize(get_export(a.id)))
        if a.cmd == "download":
            out(download(a.id, a.out))
        if a.cmd == "wait":
            row = wait_for(a.id, a.timeout)
            out(summarize(row), 0 if row.get("status") == DONE else 3)
        if a.cmd == "create":
            if a.start > a.end:
                raise ApiError("--start must not be after --end")
            created = rows(request("POST", "/api/v1/data/export", {
                "startDate": a.start, "endDate": a.end, "provider": a.provider, "format": a.format,
            }))
            if not created:
                raise ApiError("Export was not created")
            row = created[0]
            if not a.wait:
                out(summarize(row))
            row = wait_for(row["id"], a.timeout)
            result = summarize(row)
            if row.get("status") != DONE:
                out(result, 3)
            result["download"] = download(row["id"], a.out)
            out(result)
    except ApiError as e:
        out({"ok": False, "error": str(e)}, e.code)


if __name__ == "__main__":
    main()
