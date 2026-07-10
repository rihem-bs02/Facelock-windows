import argparse
import json
import socket
import sys
from pathlib import Path

from facelook.config import FaceLookConfig
from facelook.protocol import (
    PROTOCOL_VERSION,
    REQ_PING,
    REQ_AUTHENTICATE_FACE,
    encode_message,
)


def send_request_tcp(host: str, port: int, message: dict) -> dict:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client.connect((host, port))
        client.sendall(encode_message(message))

        raw = client.recv(8192)

        if not raw:
            raise RuntimeError("empty response from service")

        return json.loads(raw.decode("utf-8").strip())

    finally:
        client.close()


def send_request_unix(socket_path: Path, message: dict) -> dict:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    try:
        client.connect(str(socket_path))
        client.sendall(encode_message(message))

        raw = client.recv(8192)

        if not raw:
            raise RuntimeError("empty response from service")

        return json.loads(raw.decode("utf-8").strip())

    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="FACELOOK test client")

    parser.add_argument(
        "--transport",
        default=FaceLookConfig.TRANSPORT,
        choices=["tcp", "unix"],
        help="Transport type"
    )

    parser.add_argument(
        "--host",
        default=FaceLookConfig.HOST,
        help="TCP host"
    )

    parser.add_argument(
        "--port",
        default=FaceLookConfig.PORT,
        type=int,
        help="TCP port"
    )

    parser.add_argument(
        "--socket",
        default=str(FaceLookConfig.SOCKET_PATH),
        help="Unix socket path"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ping")

    auth_parser = subparsers.add_parser("auth")
    auth_parser.add_argument("username")

    args = parser.parse_args()

    if args.command == "ping":
        message = {
            "version": PROTOCOL_VERSION,
            "request": REQ_PING,
        }

    elif args.command == "auth":
        message = {
            "version": PROTOCOL_VERSION,
            "request": REQ_AUTHENTICATE_FACE,
            "username": args.username,
        }

    else:
        print("Unknown command.", file=sys.stderr)
        return 1

    try:
        if args.transport == "tcp":
            response = send_request_tcp(args.host, args.port, message)
        else:
            response = send_request_unix(Path(args.socket), message)

    except Exception as exc:
        print(f"[FACELOOK] Request failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())