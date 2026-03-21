from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from tinyfish_client import TinyFishAPIError, TinyFishClient
from workflow import (
    build_entry_url,
    build_goal_prompt,
    normalize_result_payload,
    normalize_vendor_list,
    vendor_name_from_url,
)


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
FINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


class AppState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, dict[str, Any]] = {}

    def create_session(self, session: dict[str, Any]) -> None:
        with self._lock:
            self._sessions[session["session_id"]] = session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return json.loads(json.dumps(session))

    def update_session(self, session_id: str, session: dict[str, Any]) -> None:
        with self._lock:
            self._sessions[session_id] = session


APP_STATE = AppState()


def get_client() -> TinyFishClient:
    api_key = os.environ.get("TINYFISH_API_KEY", "").strip()
    if not api_key:
        raise TinyFishAPIError(
            "Missing TINYFISH_API_KEY. Copy .env.example to .env and add your TinyFish key."
        )
    base_url = os.environ.get("TINYFISH_BASE_URL", "https://agent.tinyfish.ai").strip()
    return TinyFishClient(api_key=api_key, base_url=base_url)


def summarize_session(session: dict[str, Any]) -> dict[str, Any]:
    completed = 0
    failed = 0
    lowest_price = None
    cheapest_vendor = None

    for entry in session["runs"]:
        status = entry.get("status")
        if status == "COMPLETED":
            completed += 1
            price_value = _coerce_price(entry.get("result", {}).get("price"))
            if price_value is not None and (lowest_price is None or price_value < lowest_price):
                lowest_price = price_value
                cheapest_vendor = entry["vendor_name"]
        elif status in {"FAILED", "CANCELLED"}:
            failed += 1

    return {
        "total_runs": len(session["runs"]),
        "completed_runs": completed,
        "failed_runs": failed,
        "cheapest_vendor": cheapest_vendor,
        "lowest_price_value": lowest_price,
    }


def _coerce_price(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    filtered = "".join(ch for ch in value if ch.isdigit() or ch in {".", ","})
    filtered = filtered.replace(",", "")
    if not filtered:
        return None
    try:
        return float(filtered)
    except ValueError:
        return None


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._send_json({"ok": True, "time": now_iso()})
            return

        if path.startswith("/api/runs/"):
            session_id = path.removeprefix("/api/runs/")
            self._handle_get_session(session_id)
            return

        if path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/runs":
            self._handle_create_session()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unknown API route")

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def _handle_create_session(self) -> None:
        try:
            payload = self._read_json_body()
            product_query = str(payload.get("product_query", "")).strip()
            vendor_urls = normalize_vendor_list(str(payload.get("vendor_urls", "")))
            extra_notes = str(payload.get("notes", "")).strip()
            browser_profile = str(payload.get("browser_profile", "stealth")).strip().lower() or "stealth"
            country_code = str(payload.get("country_code", "")).strip().upper() or None

            if not product_query:
                self._send_json({"error": "Product query is required."}, status=HTTPStatus.BAD_REQUEST)
                return

            if len(vendor_urls) < 1:
                self._send_json(
                    {"error": "Add at least 1 vendor URL to start a scan."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            if browser_profile not in {"lite", "stealth"}:
                self._send_json(
                    {"error": "browser_profile must be either 'lite' or 'stealth'."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            client = get_client()
            session_id = str(uuid.uuid4())
            runs: list[dict[str, Any]] = []

            for vendor_url in vendor_urls:
                entry_url = build_entry_url(vendor_url, product_query)
                goal = build_goal_prompt(product_query, entry_url, extra_notes)
                response = client.create_async_run(
                    url=entry_url,
                    goal=goal,
                    browser_profile=browser_profile,
                    country_code=country_code,
                )
                runs.append(
                    {
                        "run_id": response.get("run_id"),
                        "site_url": vendor_url,
                        "entry_url": entry_url,
                        "vendor_name": vendor_name_from_url(vendor_url),
                        "status": "PENDING",
                        "result": None,
                        "error": None,
                        "goal_preview": goal,
                    }
                )

            session = {
                "session_id": session_id,
                "created_at": now_iso(),
                "product_query": product_query,
                "notes": extra_notes,
                "browser_profile": browser_profile,
                "country_code": country_code,
                "runs": runs,
            }
            APP_STATE.create_session(session)
            self._send_json(
                {
                    "session_id": session_id,
                    "message": "Runs started successfully.",
                    "session": self._serialize_session(session),
                },
                status=HTTPStatus.CREATED,
            )
        except TinyFishAPIError as exc:
            self._send_json(
                {
                    "error": str(exc),
                    "details": exc.details,
                },
                status=HTTPStatus.BAD_GATEWAY,
            )
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _handle_get_session(self, session_id: str) -> None:
        session = APP_STATE.get_session(session_id)
        if session is None:
            self._send_json({"error": "Session not found."}, status=HTTPStatus.NOT_FOUND)
            return

        pending_run_ids = [
            entry["run_id"]
            for entry in session["runs"]
            if entry.get("run_id") and entry.get("status") not in FINAL_STATUSES
        ]

        if pending_run_ids:
            try:
                client = get_client()
                batch = client.get_runs(pending_run_ids)
                by_run_id = {
                    item.get("run_id"): item
                    for item in batch.get("data", [])
                    if item.get("run_id")
                }

                for entry in session["runs"]:
                    remote = by_run_id.get(entry["run_id"])
                    if not remote:
                        continue
                    entry["status"] = remote.get("status", entry["status"])
                    if remote.get("result") is not None:
                        entry["result"] = normalize_result_payload(remote["result"])
                    if remote.get("error") is not None:
                        entry["error"] = remote["error"]

                APP_STATE.update_session(session_id, session)
            except TinyFishAPIError as exc:
                session["refresh_error"] = {
                    "message": str(exc),
                    "details": exc.details,
                }
                APP_STATE.update_session(session_id, session)

        self._send_json({"session": self._serialize_session(session)})

    def _serialize_session(self, session: dict[str, Any]) -> dict[str, Any]:
        payload = dict(session)
        payload["summary"] = summarize_session(session)
        payload["all_finished"] = all(run["status"] in FINAL_STATUSES for run in session["runs"])
        return payload

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc

    def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    load_env_file(BASE_DIR / ".env")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), AppHandler)
    print(f"VendorScout is running at http://localhost:{port}")
    if not os.environ.get("TINYFISH_API_KEY"):
        print("Warning: TINYFISH_API_KEY is not set yet. The UI will load, but runs will fail until you add it.")
    server.serve_forever()


if __name__ == "__main__":
    main()
