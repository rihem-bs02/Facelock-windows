import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoStore:
    """
    AES-256-GCM helper.

    Phase 1 uses a local development key file.

    Production rule:
    - do not leave the AES key as a plain file
    - protect it using TPM, HSM, Linux keyring, or another secure key mechanism
    """

    def __init__(self, key_path: Path):
        self.key_path = Path(key_path)
        self.key = self._load_or_create_key()

    def _load_or_create_key(self) -> bytes:
        self.key_path.parent.mkdir(parents=True, exist_ok=True)

        if self.key_path.exists():
            key = self.key_path.read_bytes()

            if len(key) != 32:
                raise ValueError("invalid AES-256 key length")

            return key

        key = AESGCM.generate_key(bit_length=256)

        fd = os.open(
            self.key_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600
        )

        with os.fdopen(fd, "wb") as file:
            file.write(key)

        return key

    def encrypt(self, plaintext: bytes) -> str:
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        payload = nonce + ciphertext
        return base64.b64encode(payload).decode("ascii")

    def decrypt(self, encrypted_b64: str) -> bytes:
        payload = base64.b64decode(encrypted_b64.encode("ascii"))

        if len(payload) < 13:
            raise ValueError("encrypted payload too short")

        nonce = payload[:12]
        ciphertext = payload[12:]

        aesgcm = AESGCM(self.key)
        return aesgcm.decrypt(nonce, ciphertext, None)