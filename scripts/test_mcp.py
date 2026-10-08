#!/usr/bin/env python3
"""End-to-end test of the finHero MCP server against a local mock of the finHero API."""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "plugins/finhero-datev-export/mcp/finhero_mcp.py"
TOKEN = "fh_live_test"
exports, puts = {}, []


class Api(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, obj=None, raw=None, headers=None):
        body = raw if raw is not None else json.dumps(obj).encode()
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authed(self):
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send(401, {"error": "Invalid API token"})
            return False
        return True

    def body(self):
        return json.loads(self.rfile.read(int(self.headers["Content-Length"])))

    def do_GET(self):
        if not self.authed():
            return
        if self.path.startswith("/api/v1/data/file"):
            return self.send(200, raw=b"PK-zip", headers={"Content-Disposition": 'attachment; filename="../DATEV_09.zip"'})
        if self.path.startswith("/api/v1/setup"):
            return self.send(200, {"providers": [{"provider": "STRIPE", "connected": True}], "ready": False})
        if "id=" in self.path:
            row = exports[int(self.path.split("id=")[1])]
            row.update(status="COMPLETED", file_name="DATEV_09.zip", transaction_count=42)
            return self.send(200, {"data": [row]})
        return self.send(200, {"data": list(exports.values())})

    def do_POST(self):
        if not self.authed():
            return
        b = self.body()
        i = len(exports) + 1
        exports[i] = {"id": i, "status": "PENDING", "start_date": b["startDate"], "end_date": b["endDate"],
                      "payment_provider": b["provider"], "export_format": b["format"]}
        self.send(200, {"data": [exports[i]]})

    def do_PUT(self):
        if not self.authed():
            return
        puts.append((self.path, self.body()))
        self.send(200, {"saved": True})


def run(token, calls):
    httpd = http.server.HTTPServer(("127.0.0.1", 0), Api)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    env = dict(os.environ, FINHERO_BASE_URL=f"http://127.0.0.1:{httpd.server_port}", FINHERO_API_TOKEN=token)
    msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}]
    msgs += [{"jsonrpc": "2.0", "id": 10 + n, "method": "tools/call", "params": {"name": name, "arguments": args}}
             for n, (name, args) in enumerate(calls)]
    out = subprocess.run([sys.executable, str(SERVER)], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                         capture_output=True, text=True, env=env, timeout=60).stdout
    httpd.shutdown()
    return {r["id"]: r for r in map(json.loads, out.splitlines())}


def text(reply):
    return reply["result"]["content"][0]["text"]


def check(cond, label):
    print(("ok   " if cond else "FAIL ") + label)
    if not cond:
        sys.exit(1)


with tempfile.TemporaryDirectory() as tmp:
    r = run(TOKEN, [
        ("check", {}),
        ("create_export", {"start_date": "2026-09-01", "end_date": "2026-09-30", "format": "datev"}),
        ("wait_for_export", {"export_id": 1}),
        ("download_export", {"export_id": 1, "directory": tmp}),
        ("create_export", {"start_date": "2026-10-01", "end_date": "2026-09-30"}),
        ("set_accounts", {"system": "DATEV", "accounts": {"consultant_no": "0012345", "debitor_account_no": 10000}, "activate": True}),
        ("setup_status", {"validate": True}),
    ])
    check(r[0]["result"]["serverInfo"]["name"] == "finhero", "initialize")
    check(len(r[1]["result"]["tools"]) == 7, "tools/list returns 7 tools")
    check(json.loads(text(r[10]))["ok"] is True, "check succeeds with token")
    check(json.loads(text(r[11]))["status"] == "PENDING", "create_export")
    waited = json.loads(text(r[12]))
    check(waited["finished"] and waited["status"] == "COMPLETED", "wait_for_export finishes")
    dl = json.loads(text(r[13]))
    check(dl["path"] == str(Path(tmp, "DATEV_09.zip")) and Path(dl["path"]).read_bytes() == b"PK-zip",
          "download_export writes the file with a sanitized name")
    check(r[14]["result"].get("isError") is True, "inverted period is rejected")
    check(puts[0][1]["accounts"] == {"consultant_no": "0012345", "debitor_account_no": "10000"} and puts[0][1]["activate"],
          "set_accounts keeps leading zeros")
    check("providers" in json.loads(text(r[16])), "setup_status")

r = run("", [("check", {})])
check(r[10]["result"].get("isError") and "Configure options" in text(r[10]), "missing token explains /plugin setup")
r = run("${user_config.api_token}", [("check", {})])
check(r[10]["result"].get("isError") is True, "unexpanded placeholder counts as missing")
r = run("fh_live_wrong", [("check", {})])
check(r[10]["result"].get("isError") and "401" in text(r[10]), "wrong token returns 401 hint")
print("all MCP tests passed")
