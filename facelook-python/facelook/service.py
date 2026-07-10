import argparse
import os
import signal
import socket
import sys
import threading
from pathlib import Path
from typing import Optional

from facelook.config import FaceLookConfig
from facelook.crypto_store import CryptoStore
from facelook.database import BiometricDatabase
from facelook.engine import MockFaceEngine, CameraFaceEngine, CameraLivenessFaceEngine
from facelook.protocol import (
    REQ_PING,
    REQ_AUTHENTICATE_FACE,
    RESULT_PONG,
    RESULT_ERROR,
    decode_message,
    encode_message,
    make_response,
)


class FaceLookService:
    def __init__(
        self,
        transport: str,
        host: str,
        port: int,
        socket_path: Path,
        engine_mode: str,
    ):
        self.transport = transport
        self.host = host
        self.port = port
        self.socket_path = Path(socket_path)
        self.engine_mode = engine_mode

        self.stop_event = threading.Event()
        self.server_socket: Optional[socket.socket] = None

        crypto = CryptoStore(FaceLookConfig.KEY_PATH)
        database = BiometricDatabase(FaceLookConfig.DATABASE_PATH, crypto)

        if engine_mode == "mock":
            self.engine = MockFaceEngine(database)
        elif engine_mode == "camera":
            self.engine = CameraFaceEngine(database)
        elif engine_mode == "liveness":
            self.engine = CameraLivenessFaceEngine(database)
        else:
            raise ValueError(f"Unsupported engine mode: {engine_mode}")

    def start(self) -> None:
        if self.transport == "tcp":
            self._start_tcp()
        elif self.transport == "unix":
            self._start_unix()
        else:
            raise ValueError(f"Unsupported transport: {self.transport}")

    def _start_tcp(self) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(FaceLookConfig.SOCKET_BACKLOG)
        self.server_socket.settimeout(1.0)

        print(f"[FACELOOK] Service listening on TCP {self.host}:{self.port}", flush=True)
        print(f"[FACELOOK] Engine mode: {self.engine_mode}", flush=True)
        print("[FACELOOK] Press Ctrl+C to stop.", flush=True)

        self._serve_forever()

    def _start_unix(self) -> None:
        self._prepare_socket_path()

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(str(self.socket_path))

        os.chmod(self.socket_path, 0o600)

        self.server_socket.listen(FaceLookConfig.SOCKET_BACKLOG)
        self.server_socket.settimeout(1.0)

        print(f"[FACELOOK] Service listening on Unix socket: {self.socket_path}", flush=True)
        print(f"[FACELOOK] Engine mode: {self.engine_mode}", flush=True)
        print("[FACELOOK] Press Ctrl+C to stop.", flush=True)

        self._serve_forever()

    def _serve_forever(self) -> None:
        while not self.stop_event.is_set():
            try:
                client_socket, _ = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            thread = threading.Thread(
                target=self._handle_client,
                args=(client_socket,),
                daemon=True,
            )
            thread.start()

        self.shutdown()

    def stop(self) -> None:
        self.stop_event.set()

        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass

    def shutdown(self) -> None:
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass

        if self.transport == "unix" and self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                pass

        print("[FACELOOK] Service stopped.", flush=True)

    def _prepare_socket_path(self) -> None:
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)

        if self.socket_path.exists():
            self.socket_path.unlink()

    def _handle_client(self, client_socket: socket.socket) -> None:
        with client_socket:
            try:
                raw = client_socket.recv(FaceLookConfig.MAX_REQUEST_BYTES)
                request = decode_message(raw)
                response = self._dispatch(request)
            except Exception as exc:
                response = make_response(
                    RESULT_ERROR,
                    reason=str(exc),
                )

            client_socket.sendall(encode_message(response))

    def _dispatch(self, request: dict) -> dict:
        request_type = request.get("request")

        if request_type == REQ_PING:
            return make_response(
                RESULT_PONG,
                reason="SERVICE_ALIVE",
            )

        if request_type == REQ_AUTHENTICATE_FACE:
            username = str(request.get("username", "")).strip()
            return self.engine.authenticate(username)

        return make_response(
            RESULT_ERROR,
            reason=f"UNKNOWN_REQUEST:{request_type}",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="FACELOOK Python biometric service")

    parser.add_argument(
        "--transport",
        default=FaceLookConfig.TRANSPORT,
        choices=["tcp", "unix"],
        help="Transport type: tcp for Windows dev, unix for Ubuntu",
    )

    parser.add_argument(
        "--host",
        default=FaceLookConfig.HOST,
        help="TCP host",
    )

    parser.add_argument(
        "--port",
        default=FaceLookConfig.PORT,
        type=int,
        help="TCP port",
    )

    parser.add_argument(
        "--socket",
        default=str(FaceLookConfig.SOCKET_PATH),
        help="Unix socket path",
    )

    parser.add_argument(
        "--engine",
        default="mock",
        choices=["mock", "camera", "liveness"],
        help="Authentication engine: mock, camera, or liveness",
    )

    args = parser.parse_args()

    service = FaceLookService(
        transport=args.transport,
        host=args.host,
        port=args.port,
        socket_path=Path(args.socket),
        engine_mode=args.engine,
    )

    def handle_signal(signum, frame):
        _ = signum
        _ = frame
        service.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())