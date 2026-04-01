"""
One-shot QA runner for remaining Module 1 checks (hits live server).
Usage: python scripts/qa_remaining.py [BASE_URL]
"""
from __future__ import annotations

import json
import sys
from typing import Any

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
ADMIN = {"Authorization": "Bearer admin_token"}


def ok(name: str, cond: bool, detail: str = "") -> bool:
    st = "PASS" if cond else "FAIL"
    print(f"  [{st}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def main() -> int:
    results: list[bool] = []
    with httpx.Client(base_url=BASE, timeout=30.0) as client:

        # --- 1. Auth verify-otp ---
        print("\n=== 1. POST /auth/verify-otp ===")
        r = client.post(
            "/auth/verify-otp",
            json={"phone": "+919876543210", "otp": "000000", "session_info": None},
        )
        d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        results.append(
            ok(
                "existing rider 200 + fields",
                r.status_code == 200
                and d.get("verified") is True
                and d.get("is_registered") is True
                and d.get("rider_name"),
                f"code={r.status_code} body={d}",
            )
        )
        # Integer rider_id preferred by spec (may be int or string)
        rid = d.get("rider_id")
        results.append(
            ok(
                "rider_id present",
                rid is not None and str(rid).isdigit(),
                str(rid),
            )
        )

        r2 = client.post(
            "/auth/verify-otp",
            json={"phone": "+918888888888", "otp": "000000", "session_info": None},
        )
        d2 = r2.json()
        results.append(
            ok(
                "new phone is_registered=false",
                r2.status_code == 200
                and d2.get("verified") is True
                and d2.get("is_registered") is False
                and d2.get("rider_id") is None,
                str(d2),
            )
        )

        # --- 2. Admin auth ---
        print("\n=== 2. Admin auth ===")
        results.append(ok("no token 403", client.get("/admin/workers").status_code == 403))
        results.append(
            ok(
                "invalid token 403",
                client.get(
                    "/admin/workers", headers={"Authorization": "Bearer wrong"}
                ).status_code
                == 403,
            )
        )
        rw = client.get("/admin/workers", headers=ADMIN)
        results.append(ok("valid token 200", rw.status_code == 200))

        # --- Workers ---
        print("\n=== 3. Admin workers ===")
        all_w = client.get("/admin/workers", headers=ADMIN).json()
        results.append(ok("GET workers list", isinstance(all_w, list)))
        filt = client.get(
            "/admin/workers",
            headers=ADMIN,
            params={"platform": "swiggy", "tier": "kavach"},
        )
        results.append(ok("filter platform+tier 200", filt.status_code == 200))
        if all_w:
            rid0 = all_w[0]["id"]
            b = client.patch(
                f"/admin/workers/{rid0}/block",
                headers=ADMIN,
                json={"is_blocked": True},
            )
            results.append(ok("block 200", b.status_code == 200))
            g = client.get(f"/admin/workers/{rid0}", headers=ADMIN).json()
            results.append(ok("blocked in DB", g.get("is_blocked") is True))
            client.patch(
                f"/admin/workers/{rid0}/block",
                headers=ADMIN,
                json={"is_blocked": False},
            )
            kv = client.patch(
                f"/admin/workers/{rid0}/verify-kyc", headers=ADMIN
            )
            results.append(ok("verify-kyc 200", kv.status_code == 200))
            g2 = client.get(f"/admin/workers/{rid0}", headers=ADMIN).json()
            results.append(ok("kyc true", g2.get("kyc_verified") is True))

        # --- Claims / payouts ---
        print("\n=== 4. Claims & payouts ===")
        live = client.get("/admin/claims/live", headers=ADMIN)
        results.append(ok("claims/live", live.status_code == 200 and isinstance(live.json(), list)))
        po = client.get("/admin/payouts", headers=ADMIN)
        results.append(ok("payouts", po.status_code == 200 and isinstance(po.json(), list)))
        ov = client.patch(
            "/admin/claims/999999/override",
            headers=ADMIN,
            json={"status": "approved"},
        )
        results.append(ok("override missing 404", ov.status_code == 404))

        # --- Fraud ---
        print("\n=== 5. Fraud ===")
        for path, keys in [
            ("/admin/fraud/flagged", ["flagged_users"]),
            ("/admin/fraud/zone-anomalies", ["anomalous_zones"]),
            ("/admin/fraud/referrals", ["suspicious_referral_clusters"]),
            ("/admin/fraud/collusion", ["collusion_rings"]),
        ]:
            fr = client.get(path, headers=ADMIN)
            j = fr.json() if fr.status_code == 200 else {}
            inner = j.get(keys[0], [])
            has_risk = any(
                "risk" in json.dumps(item).lower() or "rider_id" in item or "zone_id" in item
                for item in (inner if isinstance(inner, list) else [])
            )
            results.append(
                ok(
                    f"{path} structured",
                    fr.status_code == 200 and keys[0] in j and not any(
                        isinstance(x, str) and "todo" in x.lower() or "placeholder" in x.lower()
                        for x in _walk_strings(j)
                    ),
                    f"keys={list(j.keys())}",
                )
            )

        # --- Zones admin ---
        print("\n=== 6. Admin zones ===")
        zones = client.get("/admin/zones", headers=ADMIN).json()
        results.append(ok("admin zones has polygon", isinstance(zones, list) and (not zones or "polygon" in zones[0])))
        if zones:
            zid = zones[0]["zone_id"]
            t1 = client.patch(
                f"/admin/zones/{zid}/toggle",
                headers=ADMIN,
                json={"is_active": False},
            )
            t2 = client.patch(
                f"/admin/zones/{zid}/toggle",
                headers=ADMIN,
                json={"is_active": True},
            )
            results.append(ok("zone toggle", t1.status_code == 200 and t2.status_code == 200))
            ev = client.get(f"/admin/zones/{zid}/events", headers=ADMIN)
            results.append(ok("zone events", ev.status_code == 200 and isinstance(ev.json(), list)))

        # --- Financial ---
        print("\n=== 7. Financial analytics ===")
        fin = client.get("/admin/analytics/financial", headers=ADMIN).json()
        tp, tout = fin.get("total_premiums"), fin.get("total_payouts")
        lr = fin.get("loss_ratio")
        results.append(
            ok(
                "financial fields + loss_ratio safe",
                isinstance(tp, (int, float))
                and isinstance(tout, (int, float))
                and isinstance(lr, (int, float))
                and (tp == 0 or abs(lr - tout / tp) < 0.0001),
                str(fin),
            )
        )

        # --- Config ---
        print("\n=== 8. Admin config ===")
        cfg = client.get("/admin/config", headers=ADMIN)
        results.append(ok("GET config", cfg.status_code == 200 and "fraud_thresholds" in cfg.json()))
        patch = client.patch(
            "/admin/config",
            headers=ADMIN,
            json={"fraud_thresholds": {"high_claim_frequency": 99}, "update_message": "qa"},
        )
        results.append(ok("PATCH config 200", patch.status_code == 200))
        gcfg = client.get("/admin/config", headers=ADMIN)
        results.append(
            ok(
                "config PATCH persists on GET",
                gcfg.status_code == 200
                and gcfg.json().get("fraud_thresholds", {}).get("high_claim_frequency") == 99,
            )
        )

        # --- Polygon validation (registration) ---
        print("\n=== 9. Polygon validation /register ===")
        base_reg = {
            "partner_id": "QA-POLY-001",
            "platform": "swiggy",
            "name": "QA Poly",
            "phone": "+917111111111",
            "kyc": {"type": "aadhaar", "value": "1111"},
            "city": "Chennai",
            "zone1_id": 1,
            "zone2_id": None,
            "zone3_id": None,
            "tier": "kavach",
            "zones": [{"zone_id": 1, "polygon": [{"lat": 13.0, "lng": 80.0}, {"lat": 13.01, "lng": 80.01}]}],
        }
        bad_pts = client.post("/register", json=base_reg)
        results.append(
            ok(
                "less than 3 points rejected",
                bad_pts.status_code == 400,
                str(bad_pts.status_code),
            )
        )
        base_reg["partner_id"] = "QA-POLY-002"
        base_reg["phone"] = "+917222222222"
        base_reg["zones"] = [
            {
                "zone_id": 1,
                "polygon": [
                    {"lat": 13.0, "lng": 80.0},
                    {"lat": 13.01, "lng": 80.01},
                    {"lat": 91.0, "lng": 80.0},
                ],
            }
        ]
        bad_lat = client.post("/register", json=base_reg)
        results.append(
            ok("invalid lat rejected", bad_lat.status_code == 400, str(bad_lat.status_code))
        )
        base_reg["partner_id"] = "QA-POLY-003"
        base_reg["phone"] = "+917333333333"
        base_reg["zones"] = [
            {
                "zone_id": 1,
                "polygon": [
                    {"lat": 13.0, "lng": 80.0},
                    {"lat": 13.01, "lng": 80.01},
                    {"lat": 13.02, "lng": 181.0},
                ],
            }
        ]
        bad_lng = client.post("/register", json=base_reg)
        results.append(
            ok("invalid lng rejected", bad_lng.status_code == 400, str(bad_lng.status_code))
        )

        # --- Edge cases ---
        print("\n=== 10. Edge cases ===")
        dup = client.post(
            "/register",
            json={
                **{k: v for k, v in base_payload_reg().items() if k != "zones"},
                "partner_id": "SWG-CHN-001",
                "phone": "+919000000001",
            },
        )
        results.append(ok("duplicate partner_id 409", dup.status_code == 409))
        badz = client.post(
            "/register",
            json={
                **base_payload_reg(),
                "partner_id": "QA-ZBAD-01",
                "phone": "+919000000002",
                "zone1_id": 999999,
            },
        )
        results.append(ok("invalid zone 400", badz.status_code == 400))

    passed = sum(1 for x in results if x)
    print(f"\n>>> Summary: {passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


def base_payload_reg() -> dict[str, Any]:
    return {
        "partner_id": "QA-EDGE-X",
        "platform": "swiggy",
        "name": "Edge",
        "phone": "+919000000099",
        "kyc": {"type": "aadhaar", "value": "9999"},
        "city": "Chennai",
        "zone1_id": 1,
        "zone2_id": 2,
        "zone3_id": None,
        "tier": "kavach",
    }


def _walk_strings(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_walk_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_walk_strings(v))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
