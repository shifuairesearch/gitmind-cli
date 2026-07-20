from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


API_BASE = "https://gw.aoscdn.com/app/gitmind/v3"


class GitMindError(RuntimeError):
    def __init__(self, message: str, *, http_status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.http_status = http_status
        self.payload = payload


@dataclass
class GitMindClient:
    token: str
    timeout: int = 30

    def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json_body: Any = None) -> Any:
        url = f"{API_BASE}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        body = None
        headers = {
            "Accept": "application/json",
            "Authorization": self.token,
        }
        if json_body is not None:
            body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"message": raw[:500]}
            raise GitMindError(payload.get("message") or f"HTTP {exc.code}", http_status=exc.code, payload=payload) from exc
        except urllib.error.URLError as exc:
            raise GitMindError(str(exc.reason)) from exc

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: Any) -> Any:
        return self._request("POST", path, json_body=body)

    def put(self, path: str, body: Any) -> Any:
        return self._request("PUT", path, json_body=body)

    def require_success(self, payload: Any, action: str) -> Any:
        if isinstance(payload, dict) and payload.get("status") == 200:
            return payload.get("data")
        message = payload.get("message") if isinstance(payload, dict) else str(payload)
        raise GitMindError(f"{action} failed: {message}", payload=payload)
