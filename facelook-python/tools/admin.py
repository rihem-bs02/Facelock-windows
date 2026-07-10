import argparse
import json
import sys

from facelook.config import FaceLookConfig
from facelook.crypto_store import CryptoStore
from facelook.database import BiometricDatabase


def get_database() -> BiometricDatabase:
    crypto = CryptoStore(FaceLookConfig.KEY_PATH)
    return BiometricDatabase(FaceLookConfig.DATABASE_PATH, crypto)


def cmd_users(database: BiometricDatabase) -> int:
    users = database.list_users()

    if not users:
        print("[FACELOOK] No enrolled users.")
        return 0

    print("[FACELOOK] Enrolled users:")
    print(json.dumps(users, indent=2))
    return 0


def cmd_logs(database: BiometricDatabase, limit: int) -> int:
    logs = database.list_auth_logs(limit=limit)

    if not logs:
        print("[FACELOOK] No authentication logs.")
        return 0

    print("[FACELOOK] Authentication logs:")
    print(json.dumps(logs, indent=2))
    return 0


def cmd_stats(database: BiometricDatabase) -> int:
    stats = database.stats()
    print("[FACELOOK] Database status:")
    print(json.dumps(stats, indent=2))
    return 0


def cmd_delete(database: BiometricDatabase, username: str, permanent: bool) -> int:
    if permanent:
        deleted = database.permanently_delete_user(username)
    else:
        deleted = database.delete_user(username)

    if deleted:
        if permanent:
            print(f"[FACELOOK] Permanently deleted biometric profile for user: {username}")
        else:
            print(f"[FACELOOK] Disabled biometric profile for user: {username}")

        return 0

    print(f"[FACELOOK] No active biometric profile found for user: {username}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="FACELOOK admin tool")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("users", help="List enrolled users")

    logs_parser = subparsers.add_parser("logs", help="Show authentication logs")
    logs_parser.add_argument("--limit", type=int, default=20)

    subparsers.add_parser("stats", help="Show database statistics")

    delete_parser = subparsers.add_parser("delete", help="Delete biometric profile")
    delete_parser.add_argument("username")
    delete_parser.add_argument(
        "--permanent",
        action="store_true",
        help="Delete row permanently instead of disabling it"
    )

    args = parser.parse_args()

    database = get_database()

    if args.command == "users":
        return cmd_users(database)

    if args.command == "logs":
        return cmd_logs(database, args.limit)

    if args.command == "stats":
        return cmd_stats(database)

    if args.command == "delete":
        return cmd_delete(database, args.username, args.permanent)

    print("[FACELOOK] Unknown command.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())