import argparse
import sys
from datetime import timedelta

from .task1 import SESSION_TIMEOUT_SEC, Admin, AuditLog, Session, User, UserAccount
from .task2 import add_arguments, run

ADMINS = [
    ("netadmin", "net_admin@lpnu.ua", ["edit_firewall", "read_logs"], "N3tAdm!n2026"),
    ("auditor", "audit_team@lpnu.ua", ["read_logs"], "Aud1t#Secure"),
]


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def demo() -> int:
    audit = AuditLog()

    section("Users")
    user = User("dmytro", "dmytro_s@lpnu.ua", password="S3cure!Pass")
    admin = Admin(
        "secadmin", "admin_root@lpnu.ua", ["read_logs"], password="Adm1n#2026"
    )
    print(user)
    print(admin)

    section("Admins")
    admins = [admin] + [
        Admin(name, email, perms, password=pwd) for name, email, perms, pwd in ADMINS
    ]
    for number, item in enumerate(admins, start=1):
        print(f"{number}. {item}")

    section("Login")
    account = UserAccount(user, audit)
    print("Wrong password :", account.login("dmytro", "qwerty", "10.0.0.15"))
    print("Unknown user   :", account.login("hacker", "S3cure!Pass", "203.0.113.9"))
    print("Correct login  :", account.login("dmytro", "S3cure!Pass", "10.0.0.15"))
    print("Authenticated  :", account.is_authenticated())
    print(account["session"])

    section("Email validation")
    user.email = "dmytro_new@lpnu.ua"
    print("Changed email  :", user.email)
    for bad in ("1user@lpnu.ua", "ab@lpnu.ua", "user@localhost", "us-er@lpnu.ua"):
        try:
            user.email = bad
        except ValueError as exc:
            print("Rejected       :", exc)

    section("Admin permissions")
    admin.grant_permission("manage_users")
    admin.grant_permission("edit_firewall")
    print("After grant    :", admin)
    admin.revoke_permission("read_logs")
    print("After revoke   :", admin)
    print("edit_firewall? :", admin.has_permission("edit_firewall"))
    print("read_logs?     :", admin.has_permission("read_logs"))

    section("Item access")
    print("account['user'] :", account["user"])
    for key, value in (("password_hash", None), ("user", "not a user")):
        try:
            account[key] = value
        except (KeyError, TypeError) as exc:
            print(f"account[{key!r}] = {value!r} -> {type(exc).__name__}: {exc}")
    try:
        Session("10.0.0.1").is_active(0)
    except ValueError as exc:
        print("is_active(0)    -> ValueError:", exc)

    section("Session timeout")
    account.session.last_activity -= timedelta(seconds=SESSION_TIMEOUT_SEC + 1)
    print("Idle for       :", SESSION_TIMEOUT_SEC + 1, "sec")
    print("Authenticated  :", account.is_authenticated())

    section("Logout")
    admin_account = UserAccount(admin, audit)
    print("Admin login    :", admin_account.login("secadmin", "Adm1n#2026", "10.0.0.2"))
    admin_account.logout()
    print("Authenticated  :", admin_account.is_authenticated())
    user.deactivate()
    print("Inactive login :", account.login("dmytro", "S3cure!Pass", "10.0.0.15"))

    section("Audit log")
    audit.show_all()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m labs.lab02.main")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("demo", help="run OOP demonstration (task 1)")
    analyze = commands.add_parser("analyze", help="audit firewall rules (task 2)")
    add_arguments(analyze)
    args = parser.parse_args(argv)
    if args.command == "demo":
        return demo()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
