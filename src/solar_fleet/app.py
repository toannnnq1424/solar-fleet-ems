from __future__ import annotations

import hashlib
import hmac
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, SecretStr

from .accounts import install_accounts
from .administration import install_administration
from .agent import install_agent
from .analytics import install_analytics
from .catalog import data, native_catalog
from .controller import Controller
from .domain import Model, Principal, Role, SafetyError, utcnow
from .incident_api import install_incidents
from .management import install_management
from .runtime import install_runtime
from .security import new_session, redact, session_user, verify_password
from .workspaces import install_workspaces


class Login(Model):
    username: str = Field(min_length=1, max_length=100)
    password: SecretStr


class Preview(Model):
    device_id: str
    intent: str
    parameters: dict = Field(default_factory=dict)


class Confirmation(Model):
    plan_id: str
    digest: str
    idempotency_key: str


class HistoryQuery(Model):
    start: int
    end: int
    points: list[str] = Field(min_length=1, max_length=100)


def create_app(controller: Controller, *, port=8765, poll=True) -> FastAPI:
    store = controller.store
    assets = Path(__file__).with_name("static")

    @asynccontextmanager
    async def lifespan(app):
        if poll:
            await controller.start()
            await runtime.start()
        yield
        await runtime.close()
        await controller.close()

    app = FastAPI(
        title="Solar Fleet EMS",
        version="0.2.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    origins = {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    failures = defaultdict(deque)

    @app.middleware("http")
    async def boundaries(request: Request, call_next):
        if request.headers.get("host") not in hosts:
            return JSONResponse({"error": "host_not_allowed"}, status_code=400)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            machine = request.url.path == "/api/agent/inbox"
            if (machine and request.headers.get("origin")) or (
                not machine and request.headers.get("origin") not in origins
            ):
                return JSONResponse({"error": "origin_not_allowed"}, status_code=403)
            if len(await request.body()) > 2_000_000:
                return JSONResponse({"error": "request_too_large"}, status_code=413)
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"error": "json_required"}, status_code=415)
            if request.url.path != "/api/login" and not machine:
                session = session_user(store, request.cookies.get("solar_session"))
                if session is None or not hmac.compare_digest(
                    session[1], request.headers.get("x-csrf-token", "")
                ):
                    return JSONResponse({"error": "session_or_csrf_invalid"}, status_code=403)
        response = await call_next(request)
        response.headers.update(
            {
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
                "Cache-Control": "no-store",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
            }
        )
        return response

    @app.exception_handler(SafetyError)
    async def safety_error(request, exc):
        return JSONResponse({"error": str(exc)}, status_code=409)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI's normal error includes rejected input; never echo a login password.
        return JSONResponse({"error": "request_validation_failed"}, status_code=422)

    async def user(request: Request) -> Principal:
        session = session_user(store, request.cookies.get("solar_session"))
        if not session:
            raise HTTPException(401, "authentication_required")
        return session[0]

    async def admin(who: Principal = Depends(user)) -> Principal:
        if who.role != Role.ADMIN:
            raise HTTPException(403, "administrator_required")
        if "*" not in who.site_ids:
            raise HTTPException(403, "organization_administrator_required")
        return who

    async def operator(who: Principal = Depends(user)) -> Principal:
        if who.role not in (Role.OPERATOR, Role.ADMIN, Role.INSTALLER, Role.ENGINEER):
            raise HTTPException(403, "operator_required")
        return who

    def authorized_device(id: str, who: Principal):
        device = controller.device(id)
        if not who.can_access(device.site_id):
            raise HTTPException(403, "site_access_denied")
        return device

    @app.post("/api/login")
    async def login(body: Login, request: Request, response: Response):
        # A single loopback origin gets a shared limiter; changing the submitted username cannot evade it.
        key = request.client.host if request.client else "local"
        now = time.monotonic()
        queue = failures[key]
        while queue and queue[0] <= now - 300:
            queue.popleft()
        if len(queue) >= 8:
            raise HTTPException(429, "login_rate_limited")
        row = store.db.execute("SELECT * FROM users WHERE id=? AND active=1", (body.username,)).fetchone()
        if row is None or not verify_password(body.password.get_secret_value(), row["password_hash"]):
            queue.append(now)
            store.audit("security", {"event": "login_failed", "operator": body.username})
            raise HTTPException(401, "invalid_credentials")
        token, csrf = new_session(store, body.username)
        response.set_cookie(
            "solar_session", token, httponly=True, samesite="strict", secure=False, max_age=8 * 3600
        )
        store.audit("security", {"event": "login", "operator": body.username})
        return {"csrf": csrf}

    @app.post("/api/logout")
    async def logout(request: Request, response: Response, who=Depends(user)):
        token_hash = hashlib.sha256(request.cookies["solar_session"].encode()).hexdigest()
        store.db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
        response.delete_cookie("solar_session")
        store.audit("security", {"event": "logout", "operator": who.id})
        return {"ok": True}

    @app.get("/api/me")
    async def me(request: Request, who=Depends(user)):
        session = session_user(store, request.cookies.get("solar_session"))
        return {
            "user": who,
            "csrf": session[1],
            "writes_enabled": controller.engine.writes_enabled,
            "hardware_profiles": 0,
            "version": "0.2.0",
        }

    @app.get("/api/fleet")
    async def fleet(who=Depends(user)):
        sites = [
            {**s, **(store.get("site_profile", s["id"]) or {})}
            for s in store.list("site")
            if who.can_access(s["id"])
        ]
        devices = [d for d in store.list("device") if who.can_access(d["site_id"])]
        for d in devices:
            seen = controller.device(d["id"]).last_seen
            d["stale"] = seen is None or not -5 <= (utcnow() - seen).total_seconds() <= 300
        return {
            "sites": sites,
            "devices": devices,
            "generated_at": utcnow().isoformat(),
            "state": "NO_INTEGRATION" if not store.list("integration") else "CONFIGURED",
        }

    @app.get("/api/integrations")
    async def integrations(who=Depends(admin)):
        return [
            {
                "id": row["id"],
                "vendor": row["vendor"],
                "name": row["name"],
                "region": row["region"],
                "enabled": row["enabled"],
                "status": store.get("integration_state", row["id"]),
            }
            for row in store.list("integration")
        ]

    @app.post("/api/sync")
    async def sync(who=Depends(admin)):
        await controller.poll()
        return {"ok": True}

    @app.get("/api/devices/{id}")
    async def detail(id: str, who=Depends(user)):
        device = authorized_device(id, who)
        return {
            "device": device,
            "adapter": controller.registry.describe(device.identity.vendor),
            "latest": controller.latest(device),
            "capabilities": controller.capabilities(device),
            "control_profiles": controller.registry.profiles.explain(device),
            "bindings": [b for b in store.list("binding") if b["device_id"] == id],
        }

    @app.get("/api/devices/{id}/history")
    async def history(id: str, who=Depends(user)):
        authorized_device(id, who)
        return {"samples": store.history(id), "scope": "LOCAL_RETENTION_7_DAYS"}

    @app.post("/api/devices/{id}/history")
    async def vendor_history(id: str, body: HistoryQuery, who=Depends(user)):
        device = authorized_device(id, who)
        if "history" not in controller.registry.describe(device.identity.vendor)["features"]:
            raise SafetyError("adapter_feature_not_implemented")
        payload = await controller.adapter(device).history(
            device.vendor_id, body.start, body.end, body.points
        )
        return {"source": "VENDOR_CLOUD", "quality": "UNVERIFIED", "native": redact(payload)}

    @app.post("/api/devices/{id}/configuration")
    async def configuration(id: str, who=Depends(user)):
        device = authorized_device(id, who)
        if "configuration" not in controller.registry.describe(device.identity.vendor)["features"]:
            raise SafetyError("adapter_feature_not_implemented")
        return await controller.adapter(device).configuration(device)

    @app.post("/api/devices/{id}/alerts")
    async def alerts(id: str, who=Depends(user)):
        device = authorized_device(id, who)
        if "alarms" not in controller.registry.describe(device.identity.vendor)["features"]:
            raise SafetyError("adapter_feature_not_implemented")
        end = int(utcnow().timestamp())
        rows = await controller.adapter(device).alerts(device.vendor_id, end - 86400, end)
        payload = {"source": "VENDOR_CLOUD", "received_at": utcnow().isoformat(), "native": redact(rows)}
        store.put("alerts", id, payload)
        payload["correlation"] = controller.collect_alarms(device, rows)
        return payload

    @app.get("/api/research")
    async def research(who=Depends(user)):
        return {
            "sources": data("source-registry.json"),
            "vendors": data("vendor-matrix.json"),
            "native": native_catalog(),
            "observed_ui": data("deye-observed-ui.json"),
        }

    @app.post("/api/plans")
    async def preview(body: Preview, who=Depends(user)):
        return await controller.engine.preview(who, body.device_id, body.intent, body.parameters)

    @app.post("/api/commands", status_code=202)
    async def confirm(body: Confirmation, who=Depends(user)):
        return await controller.engine.confirm(who, body.plan_id, body.digest, body.idempotency_key)

    @app.get("/api/commands")
    async def commands(who=Depends(user)):
        return [row for row in store.commands() if who.can_access(row["site_id"])]

    @app.get("/api/audit/{category}")
    async def audit(category: str, who=Depends(user)):
        if category not in ("control", "security"):
            raise HTTPException(404)
        if category == "security":
            await admin(who)
        rows = [
            row
            for row in store.audit_rows(category)
            if (category == "security" or (row["site_id"] and who.can_access(row["site_id"])))
        ]
        return {"entries": rows, "hash_chain_valid": store.verify_audit()}

    @app.get("/")
    async def index():
        return FileResponse(assets / "index.html")

    from .data_workspace import install_data_workspace

    install_data_workspace(app, controller, user, admin)
    from .streams import install_stream

    install_stream(app, controller, origins, hosts)
    install_workspaces(app, controller, user, admin)
    install_incidents(app, controller, user)
    from .maintenance import install_maintenance

    install_maintenance(app, controller, user)
    from .schedule_planning import install_schedule_planning

    install_schedule_planning(app, controller, user)
    account_services = install_accounts(app, controller, admin)
    install_management(app, controller, user, admin)
    install_agent(app, controller)
    from .model_api import install_model_library

    install_model_library(app, controller, user)
    from .forecast_baseline import install_forecast_baseline

    install_forecast_baseline(app, controller, user)
    from .planning_configuration import install_planning_configuration

    install_planning_configuration(app, controller, user, admin)
    from .battery_health import install_battery_health
    install_battery_health(app, controller, user)
    from .tariff_engine import install_tariff_engine
    install_tariff_engine(app, controller, user)
    install_analytics(app, controller, user)
    from .reports_api import install_reports

    install_reports(app, controller, operator, user)
    from .journal_api import install_journal_api

    install_journal_api(app, controller, user, admin)
    install_administration(app, controller, user, admin)
    from .admin_api import install_admin_api

    install_admin_api(app, controller, user, admin, account_services)
    from .phase_d_api import install_phase_d_apis

    install_phase_d_apis(app, controller, user, admin)
    runtime = install_runtime(app, controller, user)
    app.state.operations_runtime = runtime
    app.mount("/static", StaticFiles(directory=assets), name="static")
    return app
