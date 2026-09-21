from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib import error, request

from guard_store import append_jsonl, now_iso, push_guard_status, write_json


def _check(
    *,
    url: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    expected: tuple[int, ...] = (200,),
    timeout: int = 8,
) -> dict[str, Any]:
    start = time.time()
    error_msg = ""
    status = 0
    attempt_used = 0
    ok = False
    for attempt in (1, 2):
        attempt_used = attempt
        try:
            req = request.Request(url, method=method)
            req.add_header("Accept", "application/json")
            if body is not None:
                req.add_header("Content-Type", "application/json")
                req.data = json.dumps(body).encode("utf-8")
            with request.urlopen(req, timeout=timeout) as resp:
                status = int(resp.status)
                ok = status in expected
        except error.HTTPError as exc:
            status = int(exc.code)
            ok = status in expected
            if not ok:
                error_msg = f"HTTP Error {status}"
        except Exception as exc:  # noqa: BLE001
            error_msg = str(exc)[:180]
        if ok:
            break
    latency_ms = int((time.time() - start) * 1000)
    return {
        "ok": ok,
        "status": status,
        "latency_ms": latency_ms,
        "attempt": attempt_used,
        "error_class": error_msg,
    }


def _targets(base: str, mode: str) -> list[tuple[str, str, str, dict[str, Any] | None, tuple[int, ...]]]:
    auth_body = {"email": "smoke@example.com", "password": "invalid-pass"}
    rows = [
        ("health", "GET", f"{base}/health", None, (200,)),
        ("cache_version", "GET", f"{base}/runtime/cache-version", None, (200, 401)),
        ("ops_status", "GET", f"{base}/runtime/ops-status", None, (200, 401)),
        ("guard_status", "GET", f"{base}/runtime/guard/status", None, (200, 401)),
        ("graphql_reach", "POST", f"{base}/graphql", {"query": "query { __typename }"}, (200, 400, 401)),
        ("auth_validation", "POST", f"{base}/auth/login", auth_body, (400, 401)),
        ("cv_extract_validation", "POST", f"{base}/search/extract-cv-text", {}, (400, 401, 415, 422)),
    ]
    if mode == "full":
        rows.extend(
            [
                ("graphql_me_unauth", "POST", f"{base}/graphql", {"query": "query { me { id } }"}, (200, 401)),
                ("graphql_favorites_unauth", "POST", f"{base}/graphql", {"query": "query { myFavorites { id jobId } }"}, (200, 401)),
                ("graphql_history_unauth", "POST", f"{base}/graphql", {"query": "query { myRecommendationHistory { id } }"}, (200, 401)),
                ("graphql_cv_jobs_unauth", "POST", f"{base}/graphql", {"query": "query { myCvJobs { jobId status } }"}, (200, 401)),
                ("auth_refresh_validation", "POST", f"{base}/auth/refresh", {"refreshToken": "invalid"}, (400, 401)),
                ("auth_register_terms_required", "POST", f"{base}/auth/register", {"email": "probe-terms@example.com", "password": "Probe1234!", "name": "Probe Terms", "acceptTerms": False}, (400, 409, 422)),
                ("profile_unauth", "GET", f"{base}/users/me", None, (401, 403)),
                ("favorites_unauth", "GET", f"{base}/favorites", None, (401, 403)),
                ("history_unauth", "GET", f"{base}/history", None, (401, 403)),
                ("report_download_unauth", "GET", f"{base}/reports/history/invalid.pdf", None, (401, 403, 404)),
                ("search_unauth", "POST", f"{base}/search", {"query": "python"}, (401, 403)),
                ("cv_jobs_unauth", "GET", f"{base}/cv-jobs", None, (401, 403)),
            ],
        )
    return rows


def run_probe(mode: str = "critical") -> dict[str, Any]:
    base = os.getenv("GUARD_API_BASE_URL", "https://api.example.com").strip().rstrip("/")
    checks = _targets(base, mode)
    results: list[dict[str, Any]] = []
    for name, method, url, body, expected in checks:
        probe = _check(url=url, method=method, body=body, expected=expected)
        results.append({"endpoint": name, "method": method, "url": url, **probe})

    failed = [r for r in results if not r["ok"]]
    counters: dict[str, int] = {
        f"{mode}_checks_total": len(results),
        f"{mode}_checks_failed_total": len(failed),
        f"{mode}_latency_total_ms": sum(int(r["latency_ms"]) for r in results),
    }
    for row in results:
        endpoint = str(row["endpoint"])
        counters[f"endpoint_{endpoint}_failed_total"] = 0 if row["ok"] else 1
        counters[f"endpoint_{endpoint}_latency_ms"] = int(row["latency_ms"])

    report = {
        "agent": "probe",
        "mode": mode,
        "generatedAt": now_iso(),
        "summary": {"total": len(results), "failed": len(failed)},
        "results": results,
        "counters": counters,
    }
    write_json(f"probe_{mode}_latest.json", report)
    append_jsonl("probe_history.jsonl", report)
    push_guard_status(report)
    return report
