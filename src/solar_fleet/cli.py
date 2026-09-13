from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

import uvicorn

from .adapters.deye import HOSTS
from .domain import Role, SafetyError
from .security import Vault, create_user, master_key
from .storage import Store


@contextmanager
def instance_lock(path: Path):
    """OS lock released on crash, unlike a stale PID file. One writer process per database."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    handle.seek(0)
    if handle.read(1) == b"":
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise SafetyError("another_controller_or_admin_process_is_using_this_data_directory") from None
    try:
        yield
    finally:
        handle.close()


def ask_password() -> str:
    value = getpass.getpass("Mật khẩu mới (ít nhất 12 ký tự): ")
    if value != getpass.getpass("Nhập lại: "):
        raise SafetyError("passwords_do_not_match")
    return value


def parser():
    p = argparse.ArgumentParser(description="Solar Fleet EMS — local controller, default READ ONLY")
    p.add_argument("--data-dir", type=Path, default=Path(os.getenv("SOLAR_DATA_DIR", "./data")))
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create first administrator and OS keyring master key")
    init.add_argument("--username", default="admin")
    user = sub.add_parser(
        "add-user", help="Add a local user; engineering rights are separate from administration"
    )
    user.add_argument("username")
    user.add_argument("--role", choices=list(Role), required=True)
    user.add_argument(
        "--site", action="append", required=True, help="Exact site ID or explicit * for all sites"
    )
    user.add_argument("--permission", action="append", default=[])
    revoke = sub.add_parser("disable-user")
    revoke.add_argument("username")
    deye = sub.add_parser(
        "add-deye", help="Prompt for OpenAPI credentials; web login cookies are never reused"
    )
    deye.add_argument("--name", required=True)
    deye.add_argument("--region", required=True, choices=list(HOSTS))
    deye.add_argument("--identity", choices=["email", "username", "mobile"], default="email")
    deye.add_argument("--company-id", type=int)
    deye.add_argument("--country-code")
    deye.add_argument(
        "--account-type", choices=["Owner", "Installer", "Company", "UNKNOWN"], default="UNKNOWN"
    )
    sub.add_parser("list-sites")
    sub.add_parser("verify-audit")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=int(os.getenv("SOLAR_PORT", "8765")))
    return p


def run(args):
    directory = args.data_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    with instance_lock(directory / "controller.lock"):
        store = Store(directory / "solar.db")
        try:
            if args.command == "init":
                if store.db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                    raise SafetyError("controller_already_initialized")
                master_key(directory, create=True)
                create_user(store, args.username, ask_password(), Role.ADMIN, ["*"])
                print("Đã khởi tạo. Chạy: solar-fleet serve. Địa chỉ mặc định http://127.0.0.1:8765")
            elif args.command == "add-user":
                create_user(store, args.username, ask_password(), Role(args.role), args.site, args.permission)
                print("Đã tạo người dùng.")
            elif args.command == "disable-user":
                with store.transaction() as db:
                    db.execute("UPDATE users SET active=0 WHERE id=?", (args.username,))
                    db.execute("DELETE FROM sessions WHERE user_id=?", (args.username,))
                store.audit("security", {"event": "user_disabled", "operator": args.username})
                print("Đã thu hồi phiên và vô hiệu hóa tài khoản.")
            elif args.command == "add-deye":
                vault = Vault(store, master_key(directory))
                print("Nhập credential Deye OpenAPI đã được cấp quyền; không dùng cookie phiên trình duyệt.")
                credentials = {
                    "app_id": getpass.getpass("App ID: "),
                    "app_secret": getpass.getpass("App Secret: "),
                    "identity_field": args.identity,
                    "identity_value": getpass.getpass(f"{args.identity}: "),
                    "password_sha256": hashlib.sha256(
                        getpass.getpass("Mật khẩu Deye: ").encode()
                    ).hexdigest(),
                    "company_id": args.company_id,
                    "country_code": args.country_code,
                }
                if any(not credentials[k] for k in ("app_id", "app_secret", "identity_value")):
                    raise SafetyError("credentials_incomplete")
                id = uuid.uuid4().hex
                vault.put(id, credentials)
                store.put(
                    "integration",
                    id,
                    {
                        "id": id,
                        "name": args.name,
                        "vendor": "Deye",
                        "region": args.region,
                        "enabled": True,
                        "account_type": args.account_type,
                        "privilege": None,
                    },
                )
                store.audit(
                    "security",
                    {"event": "integration_credentials_added", "integration_id": id, "vendor": "Deye"},
                )
                print("Đã lưu credential mã hóa. Khởi động controller để thử kết nối chỉ đọc.")
            elif args.command == "list-sites":
                for site in store.list("site"):
                    print(site["id"], site["name"])
            elif args.command == "verify-audit":
                if not store.verify_audit():
                    raise SafetyError("audit_chain_invalid")
                print("Audit hash chain hợp lệ. Không thay thế backup/checkpoint ngoài máy.")
            elif args.command == "serve":
                if not 1024 <= args.port <= 65535:
                    raise SafetyError("port_must_be_1024_to_65535")
                if not store.db.execute("SELECT 1 FROM users WHERE active=1 LIMIT 1").fetchone():
                    raise SafetyError("run_init_first")
                from .app import create_app
                from .controller import Controller

                controller = Controller(
                    store,
                    Vault(store, master_key(directory)),
                    writes_enabled=os.getenv("SOLAR_WRITES_ENABLED", "false").lower() == "true",
                )
                uvicorn.run(
                    create_app(controller, port=args.port),
                    host="127.0.0.1",
                    port=args.port,
                    workers=1,
                    proxy_headers=False,
                    access_log=False,
                    log_level="warning",
                )
        finally:
            store.close()


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        run(parser().parse_args())
    except (SafetyError, ValueError):
        # Static controlled errors only; sqlite/HTTP exception messages can expose private values.
        print("Không hoàn tất. Kiểm tra cấu hình, keyring, mật khẩu và trạng thái controller theo README.")
        raise SystemExit(1) from None
    except sqlite3.Error:
        print("Không ghi được dữ liệu hoặc tên tài khoản đã tồn tại.")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
