import argparse
import sys

from facelook.config import FaceLookConfig
from facelook.crypto_store import CryptoStore
from facelook.database import BiometricDatabase
from facelook.engine import MockFaceEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Enroll a FACELOOK mock biometric user")
    parser.add_argument("username", help="Linux username to enroll")

    args = parser.parse_args()
    username = args.username.strip()

    if not username:
        print("Username is required.", file=sys.stderr)
        return 1

    crypto = CryptoStore(FaceLookConfig.KEY_PATH)
    database = BiometricDatabase(FaceLookConfig.DATABASE_PATH, crypto)

    embedding = MockFaceEngine.generate_mock_embedding(username)
    database.save_embedding(username, embedding)

    print(f"[FACELOOK] Mock biometric profile enrolled for user: {username}")
    print("[FACELOOK] Stored encrypted embedding only. No raw image stored.")

    return 0


if __name__ == "__main__":
    sys.exit(main())