import json
from typing import Any, Dict


PROTOCOL_VERSION = 1

REQ_PING = "PING"
REQ_AUTHENTICATE_FACE = "AUTHENTICATE_FACE"


RESULT_PONG = "PONG"
RESULT_AUTH_OK = "AUTH_OK"
RESULT_AUTH_DENIED = "AUTH_DENIED"
RESULT_ERROR = "ERROR"


def make_response(
    result: str,
    *,
    confidence: float | None = None,
    reason: str | None = None,
    extra: Dict[str, Any] | None = None
) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "version": PROTOCOL_VERSION,
        "result": result,
    }

    if confidence is not None:
        response["confidence"] = round(float(confidence), 6)

    if reason is not None:
        response["reason"] = reason

    if extra:
        response.update(extra)

    return response


def encode_message(message: Dict[str, Any]) -> bytes:
    return (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")


def decode_message(raw: bytes) -> Dict[str, Any]:
    if not raw:
        raise ValueError("empty request")

    text = raw.decode("utf-8").strip()

    if not text:
        raise ValueError("blank request")

    message = json.loads(text)

    if not isinstance(message, dict):
        raise ValueError("request must be a JSON object")

    version = message.get("version")

    if version != PROTOCOL_VERSION:
        raise ValueError(f"unsupported protocol version: {version}")

    return message