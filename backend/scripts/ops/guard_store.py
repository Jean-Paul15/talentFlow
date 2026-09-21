from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib import request


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def state_dir() -> Path:
    root = os.getenv("GUARD_STATE_DIR", "/opt/talentflow-admin/state/guard").strip()
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(name: str, default: Any) -> Any:
    path = state_dir() / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(name: str, payload: Any) -> Path:
    path = state_dir() / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def append_jsonl(name: str, payload: dict[str, Any]) -> None:
    path = state_dir() / name
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def post_json(url: str, body: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 8):
    encoded = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=encoded, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    for key, value in (headers or {}).items():
        if value:
            req.add_header(key, value)
    with request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="ignore")
        return int(resp.status), text


def get_json(url: str, timeout: int = 8):
    req = request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    with request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="ignore")
        return int(resp.status), text


def gateway_base() -> str:
    return os.getenv("GUARD_API_BASE_URL", "https://api.example.com").strip().rstrip("/")


def internal_token() -> str:
    return os.getenv("RUNTIME_INTERNAL_TOKEN", "").strip()


def push_guard_status(payload: dict[str, Any]) -> None:
    headers = {"x-internal-token": internal_token()} if internal_token() else {}
    try:
        post_json(f"{gateway_base()}/runtime/guard/status", payload, headers=headers, timeout=10)
    except Exception:
        return


def toggle_maintenance(domain: str, active: bool, message: str, retry_after: int = 180) -> None:
    headers = {"x-internal-token": internal_token()} if internal_token() else {}
    body = {
        "domain": domain,
        "active": bool(active),
        "message": message,
        "retryAfterSeconds": int(retry_after),
    }
    try:
        post_json(f"{gateway_base()}/runtime/maintenance/toggle", body, headers=headers, timeout=10)
    except Exception:
        return

