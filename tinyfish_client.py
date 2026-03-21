from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request


class TinyFishAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, details: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


@dataclass
class TinyFishClient:
    api_key: str
    base_url: str = "https://agent.tinyfish.ai"

    def create_async_run(
        self,
        *,
        url: str,
        goal: str,
        browser_profile: str = "stealth",
        country_code: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            "goal": goal,
            "browser_profile": browser_profile,
        }
        if country_code:
            payload["proxy_config"] = {
                "enabled": True,
                "country_code": country_code.upper(),
            }
        return self._request("POST", "/v1/automation/run-async", payload)

    def get_runs(self, run_ids: list[str]) -> dict[str, Any]:
        if not run_ids:
            return {"data": [], "not_found": []}
        payload = {"run_ids": run_ids}
        return self._request("POST", "/v1/runs/batch", payload)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        body = None
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        http_request = request.Request(url, data=body, method=method, headers=headers)

        try:
            with request.urlopen(http_request, timeout=90) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise TinyFishAPIError(
                f"TinyFish API returned HTTP {exc.code}",
                status_code=exc.code,
                details=details,
            ) from exc
        except error.URLError as exc:
            raise TinyFishAPIError(f"Could not reach TinyFish API: {exc.reason}") from exc

        if not raw:
            return {}

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TinyFishAPIError("TinyFish API returned invalid JSON", details=raw) from exc

