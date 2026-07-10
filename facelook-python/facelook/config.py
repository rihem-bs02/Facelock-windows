from pathlib import Path
import os
import platform


class FaceLookConfig:
    """
    Cross-platform development config.

    Windows:
        Uses local TCP socket by default.

    Ubuntu:
        Uses Unix domain socket by default.
    """

    IS_WINDOWS = platform.system().lower() == "windows"

    BASE_DIR = Path(os.environ.get("FACELOOK_HOME", Path.home() / ".facelook"))

    TRANSPORT = os.environ.get(
        "FACELOOK_TRANSPORT",
        "tcp" if IS_WINDOWS else "unix"
    ).lower()

    HOST = os.environ.get("FACELOOK_HOST", "127.0.0.1")
    PORT = int(os.environ.get("FACELOOK_PORT", "8765"))

    SOCKET_PATH = Path(
        os.environ.get(
            "FACELOOK_SOCKET_PATH",
            BASE_DIR / "facelook.sock"
        )
    )

    DATABASE_PATH = Path(
        os.environ.get(
            "FACELOOK_DB_PATH",
            BASE_DIR / "facelook.db"
        )
    )

    KEY_PATH = Path(
        os.environ.get(
            "FACELOOK_KEY_PATH",
            BASE_DIR / "facelook_dev.key"
        )
    )

    EMBEDDING_SIZE = 512

    # Mock engine threshold
    MATCH_THRESHOLD = 0.85

    # Camera PoC settings
    ENROLLMENT_SAMPLE_COUNT = 5
    AUTH_SAMPLE_COUNT = 3
    CAMERA_MATCH_THRESHOLD = 0.70

    SOCKET_BACKLOG = 10
    MAX_REQUEST_BYTES = 8192