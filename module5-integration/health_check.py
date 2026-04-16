#!/usr/bin/env python3
"""
health_check.py — RahatPay Phase 3 Integration Health Check (Part D1)
======================================================================
Checks liveness of all three backend modules and reports status.

Port Reference (AUTHORITATIVE):
  Module 1 — Registration & Admin  → http://localhost:8000
  Module 2 — Risk Engine & ML      → http://localhost:8002
  Module 3 — Triggers & Claims     → http://localhost:8003
  Admin Dashboard (Vite dev)        → http://localhost:5000

Usage:
    python health_check.py
    python health_check.py --json       # JSON output for CI/CD integration
    python health_check.py --watch 15   # Poll every 15 seconds
    python health_check.py --retries 3  # Retry failed checks up to N times
"""

import sys
import json
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


MODULES = [
    {
        "name": "Module 1 — Registration & Admin",
        "port": 8000,
        "health_url": "http://localhost:8000/health",   # :8000
        "key": "module1",
    },
    {
        "name": "Module 2 — Risk Engine & ML",
        "port": 8002,
        "health_url": "http://localhost:8002/health",   # :8002
        "key": "module2",
    },
    {
        "name": "Module 3 — Triggers & Claims",
        "port": 8003,
        "health_url": "http://localhost:8003/health",   # :8003
        "key": "module3",
    },
]

CRITICAL_ENDPOINTS = [
    # (module_key, method, url, description)
    # Note: health_check.py hits backend ports directly (not via Vite proxy).
    # The /m3 prefix is a Vite proxy convention only — direct calls use :8003/admin/...
    ("module1", "GET",  "http://localhost:8000/admin/analytics/actuarial", "Actuarial analytics"),
    ("module1", "GET",  "http://localhost:8000/admin/zones",                "Zone list"),
    ("module1", "POST", "http://localhost:8000/admin/stress-test",          "BCR stress test"),
    ("module3", "GET",  "http://localhost:8003/api/triggers/polling-log",   "Trigger polling log"),
    ("module3", "GET",  "http://localhost:8003/admin/claims/live",          "Live claims (M3)"),
    ("module3", "GET",  "http://localhost:8003/admin/fraud/summary",        "Fraud summary (M3)"),
]


def check_url(url: str, method: str = "GET", headers: dict = None, body: bytes = None,
              timeout: int = 5, retries: int = 1):
    """Performs an HTTP request and returns (ok: bool, status_code: int, latency_ms: float).
    Retries up to `retries` times on network error (not on HTTP error).
    """
    for attempt in range(max(1, retries)):
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", "Bearer admin_token")
        req.add_header("Content-Type", "application/json")
        if body:
            req.data = body

        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                latency_ms = (time.monotonic() - t0) * 1000
                return True, resp.status, latency_ms
        except urllib.error.HTTPError as e:
            latency_ms = (time.monotonic() - t0) * 1000
            # 4xx responses still mean the server is UP
            return (e.code < 500), e.code, latency_ms
        except Exception:
            latency_ms = (time.monotonic() - t0) * 1000
            if attempt < retries - 1:
                time.sleep(0.5 * (attempt + 1))  # simple exponential backoff
                continue
            return False, 0, latency_ms
    return False, 0, 0.0  # unreachable


def run_health_check(as_json: bool = False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = {}
    all_healthy = True

    if not as_json:
        print(f"\n{BOLD}{CYAN}{'═' * 60}{RESET}")
        print(f"{BOLD}{CYAN}  RahatPay Phase 3 — Integration Health Check{RESET}")
        print(f"{CYAN}  {timestamp}{RESET}")
        print(f"{CYAN}{'═' * 60}{RESET}\n")
        print(f"  {'Module':<42} {'Status':<12} {'Latency'}")
        print(f"  {'──────':<42} {'──────':<12} {'───────'}")

    for mod in MODULES:
        ok, code, ms = check_url(mod["health_url"])
        results[mod["key"]] = {
            "name": mod["name"],
            "port": mod["port"],
            "healthy": ok,
            "status_code": code,
            "latency_ms": round(ms, 1),
        }
        if not ok:
            all_healthy = False

        if not as_json:
            status_str = f"{GREEN}● ONLINE{RESET}" if ok else f"{RED}● OFFLINE{RESET}"
            latency_str = f"{ms:.0f}ms" if ok else "—"
            print(f"  {mod['name']:<42} {status_str:<20} {latency_str}")

    if not as_json:
        print(f"\n  {'Critical Endpoint':<50} {'Status'}")
        print(f"  {'─────────────────':<50} {'──────'}")

    endpoint_results = []
    for mod_key, method, url, desc in CRITICAL_ENDPOINTS:
        mod_online = results.get(mod_key, {}).get("healthy", False)
        if not mod_online:
            ep_result = {"description": desc, "url": url, "status": "SKIPPED (module offline)"}
            if not as_json:
                print(f"  {desc:<50} {YELLOW}⊘ SKIPPED{RESET}")
        else:
            body = b'{"sim_days": 14, "severity": 0.75}' if method == "POST" else None
            ok, code, ms = check_url(url, method=method, body=body)
            ep_result = {
                "description": desc,
                "url": url,
                "status": "OK" if ok else "FAILED",
                "status_code": code,
                "latency_ms": round(ms, 1),
            }
            if not as_json:
                s = f"{GREEN}✓ OK ({code}, {ms:.0f}ms){RESET}" if ok else f"{RED}✗ FAILED ({code}){RESET}"
                print(f"  {desc:<50} {s}")
        endpoint_results.append(ep_result)

    overall = "HEALTHY" if all_healthy else "DEGRADED"

    if not as_json:
        color = GREEN if all_healthy else RED
        print(f"\n  {BOLD}Overall status: {color}{overall}{RESET}\n")
        print(f"  {CYAN}{'═' * 60}{RESET}\n")
    else:
        output = {
            "timestamp": timestamp,
            "overall": overall,
            "modules": results,
            "endpoints": endpoint_results,
        }
        print(json.dumps(output, indent=2))

    return 0 if all_healthy else 1


def main():
    parser = argparse.ArgumentParser(description="RahatPay integration health check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--watch", type=int, metavar="SECONDS", help="Poll continuously")
    parser.add_argument("--retries", type=int, default=1, metavar="N", help="Retry failed checks N times")
    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                run_health_check(as_json=args.json)
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nHealth check stopped.")
            sys.exit(0)
    else:
        sys.exit(run_health_check(as_json=args.json))


if __name__ == "__main__":
    main()
