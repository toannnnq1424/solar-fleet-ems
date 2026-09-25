"""Administration, User Management, Cloud Accounts, Site Configuration, and Device Onboarding API.

Covers:
- Mockup #19: User Management & RBAC Permissions Matrix, 4 KPI cards, Security Audit Logs
- Mockup #21: Vendor Cloud Accounts, Live Diagnostic Connection Test Inspector, API Keys, Local Agent Certs, Vault
- Mockup #15: Site Configuration, TOU Tariff Rates, Operating Modes, Backup EPS, Reserve SOC, Multi-channel Notifications
- Mockup #13: 4-Step Device Onboarding & Commissioning Wizard with Topology Tree Preview and Technical Connectivity Checks

Implementation scope:
- Saved settings are local drafts and do not prove device compatibility.
- Zero emojis: 100% SVG vector icons in UI.
- Strict RBAC and audit logging with SHA-256 hash-chain verification.
"""

from __future__ import annotations

import csv
import io
import json
import math
import urllib.parse
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .domain import Role


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


CANONICAL_ROLES = [
    {
        "role": Role.VIEWER.value,
        "name_vi": "Người xem (Viewer)",
        "description": "Chỉ xem dữ liệu đo lường, không được gửi lệnh điều khiển hoặc thay đổi cấu hình.",
        "badge_color": "gray",
        "permissions": {
            "view_data": True,
            "quick_control": False,
            "edit_tou": False,
            "grid_settings": False,
            "bulk_rollout": False,
            "manage_credentials": False,
            "view_security_log": False,
        },
    },
    {
        "role": Role.OPERATOR.value,
        "name_vi": "Người vận hành (Operator)",
        "description": "Vận hành điều khiển nhanh, chuyển chế độ nạp xả trong phạm vi an toàn.",
        "badge_color": "orange",
        "permissions": {
            "view_data": True,
            "quick_control": True,
            "edit_tou": True,
            "grid_settings": False,
            "bulk_rollout": True,
            "manage_credentials": False,
            "view_security_log": False,
        },
    },
    {
        "role": Role.INSTALLER.value,
        "name_vi": "Kỹ thuật lắp đặt (Installer)",
        "description": "Lắp đặt, nghiệm thu trạm, cấu hình lịch TOU và kết nối phần cứng tại hiện trường.",
        "badge_color": "green",
        "permissions": {
            "view_data": True,
            "quick_control": True,
            "edit_tou": True,
            "grid_settings": False,
            "bulk_rollout": True,
            "manage_credentials": False,
            "view_security_log": False,
        },
    },
    {
        "role": Role.ENGINEER.value,
        "name_vi": "Kỹ sư cao cấp (Senior Engineer)",
        "description": "Cấu hình sâu lưới điện, triển khai chiến dịch hàng loạt và phân tích sự cố chuyên sâu.",
        "badge_color": "blue",
        "permissions": {
            "view_data": True,
            "quick_control": True,
            "edit_tou": True,
            "grid_settings": False,
            "bulk_rollout": True,
            "manage_credentials": False,
            "view_security_log": False,
        },
    },
    {
        "role": Role.ADMIN.value,
        "name_vi": "Quản trị viên (Administrator)",
        "description": "Quản lý toàn bộ tài khoản người dùng, phân quyền, quản lý khóa và xem vết kiểm toán bảo mật.",
        "badge_color": "red",
        "permissions": {
            "view_data": True,
            "quick_control": False,
            "edit_tou": True,
            "grid_settings": False,
            "bulk_rollout": True,
            "manage_credentials": True,
            "view_security_log": True,
        },
    },
]


def _default_site_config(site_id: str, site_name: str = "") -> dict:
    return {
        "site_id": site_id,
        "site_name": site_name or site_id,
        "rated_capacity_kw": None,
        "state": "DRAFT",
        "dispatch_enabled": False,
        "tou_rates": {},
        "operating_goals": {},
        "backup_eps": {},
        "battery_limits": {},
        "data_sync": {},
        "notifications": {"channels": {}, "recipient_emails": "", "recipient_phones": ""},
        "ownership": {},
        "units": {"power": "kW", "energy": "kWh", "currency": "VND"},
    }


def _build_site_checklist(cfg: dict) -> list[dict]:
    # A saved form is a draft, not an electrical compatibility or commissioned-control proof.
    return [
        {"item": key, "valid": False, "status": "REVIEW_REQUIRED" if cfg.get(key) else "NOT_CONFIGURED"}
        for key in (
            "tou_rates",
            "operating_goals",
            "backup_eps",
            "battery_limits",
            "data_sync",
            "notifications",
            "ownership",
        )
    ]


class SiteConfigForm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str | None = None
    site_name: str | None = None
    rated_capacity_kw: float | None = Field(None, ge=0, le=10_000_000, allow_inf_nan=False)
    tou_rates: dict | None = None
    operating_goals: dict | None = None
    backup_eps: dict | None = None
    battery_limits: dict | None = None
    data_sync: dict | None = None
    notifications: dict | None = None
    ownership: dict | None = None
    units: dict | None = None


class OnboardScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vendor: str = "growatt"
    connection_mode: str | None = "cloud_api"
    host: str | None = None
    port: int | None = 502
    slave_id: int | None = 1
    serial_number: str | None = None
    site_id: str | None = None


class OnboardCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str
    vendor: str = "deye"
    device_type: str = "hybrid_inverter"
    device_name: str
    serial_number: str
    model: str | None = None
    rated_ac_kw: float | None = None
    battery_capacity_kwh: float | None = 0.0
    connection_mode: str | None = "cloud_api"
    host: str | None = None
    port: int | None = 502
    slave_id: int | None = 1
    firmware_version: str | None = None
    location: str | None = None
    integration_id: str | None = None


def install_admin_api(app, controller, user_dep, admin_dep, account_services):
    store = controller.store

    @app.get("/api/admin/summary")
    async def get_admin_summary(who=Depends(admin_dep)):
        users_rows = store.db.execute("SELECT * FROM users").fetchall()
        total_users = len(users_rows)
        active_users = sum(1 for r in users_rows if bool(r["active"]))

        roles_count = len(CANONICAL_ROLES)

        integrations = store.list("integration")
        linked_cloud_accounts = len(integrations)

        sensitive_perms = {"grid_settings", "raw_commands", "firmware_upgrade", "battery_settings"}
        sensitive_count = 0
        for r in users_rows:
            perms = json.loads(r["permissions"]) if r["permissions"] else []
            if any(p in sensitive_perms for p in perms):
                sensitive_count += 1

        hash_valid = store.verify_audit()
        total_audit_events = len(store.audit_rows("security")) + len(store.audit_rows("control"))

        vault_ok = True
        try:
            for i in integrations:
                controller.vault.get(i["id"])
        except Exception:
            vault_ok = False

        sites_count = len(store.list("site"))

        return {
            "total_users": total_users,
            "active_users": active_users,
            "roles_count": roles_count,
            "linked_cloud_accounts": linked_cloud_accounts,
            "sensitive_perms_count": sensitive_count,
            "hash_chain_valid": hash_valid,
            "total_audit_events": total_audit_events,
            "vault_status": "encrypted_db" if vault_ok else "degraded",
            "vault": {
                "state": "AVAILABLE" if vault_ok else "DEGRADED",
                "encryption": "Fernet (AES-128-CBC + HMAC-SHA256)",
                "encrypted_items_count": len(integrations),
                "browser_secret_access": False,
            },
            "sites_count": sites_count,
        }

    @app.get("/api/admin/users")
    async def get_admin_users(
        q: str | None = None,
        role: str | None = None,
        status: str | None = None,
        site_id: str | None = None,
        page: int = Query(1, ge=1),
        limit: int = Query(25, ge=1, le=100),
        who=Depends(admin_dep),
    ):
        users_rows = store.db.execute("SELECT * FROM users ORDER BY id").fetchall()
        sites_map = {s["id"]: s.get("name", s["id"]) for s in store.list("site")}

        # Find latest login per user from audit log
        security_audit = store.audit_rows("security")
        last_logins = {}
        for a in security_audit:
            b = a.get("body", {})
            if b.get("event") == "login":
                u = b.get("operator") or b.get("user")
                if u and u not in last_logins:
                    last_logins[u] = b.get("timestamp") or a.get("timestamp")

        enriched_users = []
        for r in users_rows:
            uid = r["id"]
            user_sites = (
                json.loads(r["sites"])
                if ("sites" in r.keys() and r["sites"])
                else (json.loads(r["site_ids"]) if ("site_ids" in r.keys() and r["site_ids"]) else [])
            )
            user_perms = (
                json.loads(r["permissions"]) if ("permissions" in r.keys() and r["permissions"]) else []
            )
            has_2fa = bool(r["two_factor_secret"]) if "two_factor_secret" in r.keys() else False
            last_login = last_logins.get(uid)

            # Role details
            role_val = r["role"]
            canonical = next((c for c in CANONICAL_ROLES if c["role"].lower() == role_val.lower()), None)
            role_name_vi = canonical["name_vi"] if canonical else role_val

            site_names = [sites_map.get(sid, sid) for sid in user_sites if sid != "*"]

            enriched_users.append(
                {
                    "id": uid,
                    "name": uid.capitalize(),
                    "email": None,
                    "role": role_val,
                    "role_name_vi": role_name_vi,
                    "active": bool(r["active"]),
                    "site_ids": user_sites,
                    "site_names": site_names,
                    "sites_label": "Toàn bộ trạm" if "*" in user_sites else (", ".join(site_names) or "—"),
                    "permissions": user_perms,
                    "two_factor_enabled": has_2fa,
                    "last_login_at": last_login,
                    "last_login": last_login,
                    "is_current_user": (uid == who.id),
                }
            )

        # Apply search and filters
        filtered = enriched_users
        if q:
            query = q.lower().strip()
            filtered = [
                u
                for u in filtered
                if query in u["id"].lower()
                or query in (u["email"] or "").lower()
                or query in u["sites_label"].lower()
            ]
        if role and role != "ALL":
            filtered = [u for u in filtered if u["role"].lower() == role.lower()]
        if status and status != "ALL":
            if status.lower() == "active":
                filtered = [u for u in filtered if u["active"]]
            elif status.lower() == "disabled":
                filtered = [u for u in filtered if not u["active"]]
        if site_id and site_id != "ALL":
            filtered = [u for u in filtered if "*" in u["site_ids"] or site_id in u["site_ids"]]

        total_items = len(filtered)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit

        return {
            "total_items": total_items,
            "total_pages": max(1, math.ceil(total_items / limit)),
            "current_page": page,
            "items": filtered[start_idx:end_idx],
        }

    @app.get("/api/admin/roles-matrix")
    async def get_roles_matrix(who=Depends(admin_dep)):
        return {
            "roles": CANONICAL_ROLES,
            "permissions_catalog": [
                {
                    "key": "view_data",
                    "name_vi": "Xem dữ liệu",
                    "description": "Xem báo cáo và viễn trắc thiết bị",
                },
                {
                    "key": "quick_control",
                    "name_vi": "Điều khiển nhanh",
                    "description": "Đổi chế độ nạp xả, bật tắt nhanh",
                },
                {
                    "key": "edit_tou",
                    "name_vi": "Chỉnh TOU",
                    "description": "Soạn thảo biểu giá điện và lịch tuần",
                },
                {
                    "key": "grid_settings",
                    "name_vi": "Chỉnh grid setting",
                    "description": "Thông số hòa lưới và bảo vệ",
                },
                {
                    "key": "bulk_rollout",
                    "name_vi": "Bulk rollout",
                    "description": "Triển khai chiến dịch đa nhà máy",
                },
                {
                    "key": "manage_credentials",
                    "name_vi": "Quản lý credentials",
                    "description": "Quản lý user, token, API key",
                },
                {
                    "key": "view_security_log",
                    "name_vi": "Xem security log",
                    "description": "Xem vết kiểm toán mật mã SHA-256",
                },
            ],
        }

    @app.get("/api/admin/cloud-accounts")
    async def get_admin_cloud_accounts(who=Depends(admin_dep)):
        result = await account_services["overview"](who)
        rows = []
        for record in result["accounts"]:
            state, diagnostic = record.get("status") or {}, record.get("diagnostic") or {}
            rows.append(
                {
                    "id": record["id"],
                    "vendor": record["vendor"],
                    "brand": record["vendor"],
                    "brand_name": record["vendor"],
                    "name": record["name"],
                    "account": record["account"],
                    "account_mask": record["account"],
                    "scope": "READ_ONLY",
                    "mode": "cloud",
                    "status": state.get("status", "UNKNOWN"),
                    "token_status": "UNKNOWN",
                    "token_valid": None,
                    "token_expiry": None,
                    "plants_count": record["plant_count"],
                    "last_sync": state.get("last_success"),
                    "sync_status": state.get("status", "UNKNOWN"),
                    "diagnostic": diagnostic,
                }
            )
        return {
            "accounts": rows,
            "items": rows,
            "total": len(rows),
            "total_connected": sum(r["status"] == "HEALTHY" for r in rows),
            "certificates_count": result["certificates"]["count"],
            "api_keys_count": result["active_keys"],
            "vault_state": result["vault"]["state"],
        }

    @app.post("/api/admin/cloud-accounts/check")
    async def check_cloud_account(body: dict, who=Depends(admin_dep)):
        result = await account_services["check"](str(body.get("account_id", "")), who)
        return {
            **result,
            "success": result["state"] == "PASS",
            "latency_ms": result["duration_ms"],
            "criteria": {
                c["key"]: {"success": c["state"] == "PASS", "detail": c["state"]} for c in result["checks"]
            },
        }

    @app.get("/api/admin/security-log")
    async def get_admin_security_log(limit: int = Query(20, ge=1, le=100), who=Depends(admin_dep)):
        raw_audit = store.audit_rows("security")
        formatted = []
        for idx, r in enumerate(raw_audit[:limit]):
            b = r.get("body", {})
            event = b.get("event", "security_action")
            user_act = b.get("operator") or b.get("user") or "system"
            details = b.get("details") or b.get("role") or b.get("site_ids") or "Thao tác xác thực hệ thống"
            if isinstance(details, list):
                details = ", ".join(str(x) for x in details)

            formatted.append(
                {
                    "id": r.get("seq", idx + 1),
                    "timestamp": b.get("timestamp") or r.get("timestamp") or None,
                    "user": user_act,
                    "user_id": user_act,
                    "action": event,
                    "action_label": {
                        "login": "Đăng nhập thành công",
                        "login_failed": "Đăng nhập thất bại",
                        "logout": "Đăng xuất",
                        "user_created": "Tạo người dùng mới",
                        "user_access_changed": "Thay đổi phân quyền",
                        "password_reset": "Đặt lại mật khẩu",
                        "user_enabled_changed": "Thay đổi trạng thái tài khoản",
                        "site_config_updated": "Cập nhật cấu hình nhà máy",
                    }.get(event, event),
                    "action_label_vi": {
                        "login": "Đăng nhập thành công",
                        "login_failed": "Đăng nhập thất bại",
                        "logout": "Đăng xuất",
                        "user_created": "Tạo người dùng mới",
                        "user_access_changed": "Thay đổi phân quyền",
                        "password_reset": "Đặt lại mật khẩu",
                        "user_enabled_changed": "Thay đổi trạng thái tài khoản",
                        "site_config_updated": "Cập nhật cấu hình nhà máy",
                    }.get(event, event),
                    "details": details,
                    "ip_address": b.get("ip_address"),
                    "row_hash": r.get("hash"),
                    "status": "FAILED" if "fail" in event else "SUCCESS",
                }
            )

        return {
            "hash_chain_valid": store.verify_audit(),
            "total_items": len(formatted),
            "items": formatted,
            "entries": formatted,
        }

    @app.get("/api/admin/site-config/{site_id}")
    async def get_site_config(site_id: str, who=Depends(user_dep)):
        site = store.get("site", site_id)
        if not site:
            # If site doesn't exist yet, build initial template
            raise HTTPException(404, "site_not_found")

        if not who.can_access(site_id):
            raise HTTPException(403, "site_access_denied")

        saved_config = store.get("site_config", site_id) or {}
        default_cfg = _default_site_config(site_id, site.get("name", site_id))
        merged_cfg = {**default_cfg, **saved_config}

        checklist = _build_site_checklist(merged_cfg)

        return {
            "site_id": site_id,
            "site": site,
            "config": merged_cfg,
            "checklist": checklist,
            "all_valid": all(c["valid"] for c in checklist),
        }

    @app.post("/api/admin/site-config/{site_id}")
    async def update_site_config(site_id: str, body: SiteConfigForm, who=Depends(admin_dep)):
        site = store.get("site", site_id)
        if not site:
            raise HTTPException(404, "site_not_found")

        if not who.can_access(site_id):
            raise HTTPException(403, "site_access_denied")

        if body.site_id is not None and body.site_id != site_id:
            raise HTTPException(422, "site_identity_mismatch")
        data_dict = body.model_dump(exclude_unset=True, exclude={"site_id"})

        # Draft percentage validation; actual device limits are checked by the command engine.
        bat = data_dict.get("battery_limits") or {}
        eps = data_dict.get("backup_eps") or {}
        soc = bat.get("reserve_soc_pct")
        if soc is None:
            soc = eps.get("reserve_soc_min")

        if soc is not None:
            try:
                soc_val = float(soc)
                if not math.isfinite(soc_val) or soc_val < 0 or soc_val > 100:
                    return JSONResponse(
                        {
                            "error": "reserve_soc_out_of_percent_range (0-100); hardware constraints require preview"
                        },
                        status_code=400,
                    )
            except (TypeError, ValueError):
                raise HTTPException(422, "invalid_soc") from None

        saved = store.get("site_config", site_id) or _default_site_config(site_id, site.get("name", site_id))
        new_data = {
            **saved,
            **data_dict,
            "site_id": site_id,
            "updated_at": utcnow().isoformat(),
            "state": "DRAFT",
            "dispatch_enabled": False,
        }
        for key, val in data_dict.items():
            if isinstance(val, dict):
                new_data[key] = {**(saved.get(key) or {}), **val}

        with store.transaction():
            store.put("site_config", site_id, new_data)
            if data_dict.get("site_name"):
                site_update = {**site, "name": data_dict["site_name"]}
                store.put("site", site_id, site_update)

            store.audit(
                "security",
                {"event": "site_config_updated", "operator": who.id, "site_id": site_id},
                site_id,
            )

        checklist = _build_site_checklist(new_data)
        return {
            "ok": True,
            "site_id": site_id,
            "config": new_data,
            "checklist": checklist,
            "updated_at": new_data["updated_at"],
        }

    @app.post("/api/admin/devices/onboard-scan")
    async def onboard_scan_devices(body: OnboardScanRequest, who=Depends(admin_dep)):
        raise HTTPException(409, "use_integrations_check_and_sync_for_authenticated_discovery")

    @app.post("/api/admin/devices/onboard-complete")
    async def onboard_complete_device(body: OnboardCompleteRequest, who=Depends(admin_dep)):
        if not who.can_access(body.site_id):
            raise HTTPException(403, "site_access_denied")
        if not store.get("site", body.site_id):
            raise HTTPException(404, "site_not_found")
        # A manually entered serial is not device discovery and cannot create a valid runtime Device.
        matches = [
            d
            for d in controller.devices()
            if d.site_id == body.site_id
            and d.integration_id == body.integration_id
            and d.vendor_id == body.serial_number
        ]
        if len(matches) != 1:
            raise HTTPException(409, "authenticated_device_discovery_required")
        device = matches[0]
        if device.identity.vendor.lower() != body.vendor.lower():
            raise HTTPException(422, "device_vendor_mismatch")
        device.name = body.device_name
        with store.transaction():
            store.put("device", device.id, device.model_dump(mode="json"))
            store.audit(
                "operations",
                {"event": "device_named", "device_id": device.id, "operator": who.id},
                body.site_id,
            )
        return {"success": True, "device_id": device.id, "site_id": body.site_id, "commissioned": False}

    @app.get("/api/admin/export-users")
    async def export_users_csv(who=Depends(admin_dep)):
        users_rows = store.db.execute("SELECT * FROM users ORDER BY id").fetchall()
        output = io.StringIO()
        output.write("\ufeff")  # UTF-8 BOM
        writer = csv.writer(output)
        writer.writerow(
            [
                "Tài khoản (ID)",
                "Họ tên",
                "Vai trò (Role)",
                "Trạng thái (Active)",
                "Phạm vi trạm (Sites)",
                "Quyền nhạy cảm (Permissions)",
                "Xác thực 2FA",
                "Tạo lúc (Created At)",
            ]
        )

        for r in users_rows:
            uid = r["id"]
            user_sites = (
                json.loads(r["sites"])
                if ("sites" in r.keys() and r["sites"])
                else (json.loads(r["site_ids"]) if ("site_ids" in r.keys() and r["site_ids"]) else [])
            )
            user_perms = (
                json.loads(r["permissions"]) if ("permissions" in r.keys() and r["permissions"]) else []
            )
            has_2fa = bool(r["two_factor_secret"]) if "two_factor_secret" in r.keys() else False
            writer.writerow(
                [
                    "'" + uid if uid.startswith(("=", "+", "-", "@")) else uid,
                    "'" + uid.capitalize() if uid.startswith(("=", "+", "-", "@")) else uid.capitalize(),
                    r["role"],
                    "Đang hoạt động" if r["active"] else "Tạm khóa",
                    "Toàn bộ trạm" if "*" in user_sites else (", ".join(user_sites) or "—"),
                    ", ".join(user_perms) or "—",
                    "Đã bật" if has_2fa else "Chưa bật",
                    r["created_at"] if "created_at" in r.keys() else None,
                ]
            )

        content = output.getvalue()
        filename = f"users_export_{utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        ascii_fallback = "users_export.csv"
        rfc5987_filename = urllib.parse.quote(filename, encoding="utf-8")

        headers = {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{rfc5987_filename}",
        }
        return Response(content=content, headers=headers)
