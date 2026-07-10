import hashlib
import time

import numpy as np

from facelook.camera import CameraManager
from facelook.config import FaceLookConfig
from facelook.database import BiometricDatabase
from facelook.embedding import SimpleFaceEmbedder
from facelook.embedding_utils import average_embeddings
from facelook.face_detector import FaceDetector
from facelook.liveness import BasicMotionLivenessDetector
from facelook.matcher import normalize_embedding, is_match
from facelook.protocol import (
    RESULT_AUTH_OK,
    RESULT_AUTH_DENIED,
    make_response,
)


class MockFaceEngine:
    """
    Phase 1 mock biometric engine.
    """

    def __init__(self, database: BiometricDatabase):
        self.database = database

    @staticmethod
    def generate_mock_embedding(
        username: str,
        size: int = FaceLookConfig.EMBEDDING_SIZE
    ) -> np.ndarray:
        digest = hashlib.sha256(username.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big", signed=False)

        rng = np.random.default_rng(seed)
        embedding = rng.normal(0, 1, size).astype(np.float32)

        return normalize_embedding(embedding)

    def authenticate(self, username: str) -> dict:
        username = username.strip()

        if not username:
            self.database.log_auth(None, RESULT_AUTH_DENIED, 0.0, "USERNAME_REQUIRED")
            return make_response(RESULT_AUTH_DENIED, confidence=0.0, reason="USERNAME_REQUIRED")

        stored_embedding = self.database.load_embedding(username)

        if stored_embedding is None:
            self.database.log_auth(username, RESULT_AUTH_DENIED, 0.0, "USER_NOT_ENROLLED")
            return make_response(RESULT_AUTH_DENIED, confidence=0.0, reason="USER_NOT_ENROLLED")

        live_embedding = self.generate_mock_embedding(username)

        matched, confidence = is_match(
            live_embedding,
            stored_embedding,
            FaceLookConfig.MATCH_THRESHOLD
        )

        if matched:
            self.database.log_auth(username, RESULT_AUTH_OK, confidence, "MOCK_FACE_MATCH")
            return make_response(RESULT_AUTH_OK, confidence=confidence, reason="MOCK_FACE_MATCH")

        self.database.log_auth(username, RESULT_AUTH_DENIED, confidence, "MOCK_FACE_NOT_MATCHED")
        return make_response(RESULT_AUTH_DENIED, confidence=confidence, reason="MOCK_FACE_NOT_MATCHED")


class CameraFaceEngine:
    """
    Phase 2 camera-based biometric engine.
    """

    def __init__(self, database: BiometricDatabase):
        self.database = database
        self.detector = FaceDetector()
        self.embedder = SimpleFaceEmbedder()

    def capture_live_embedding(
        self,
        camera_index: int = 0,
        timeout_seconds: float = 10.0,
        sample_count: int = FaceLookConfig.AUTH_SAMPLE_COUNT
    ) -> tuple[np.ndarray | None, str]:
        camera = CameraManager(camera_index=camera_index)

        if not camera.open():
            return None, "CAMERA_OPEN_FAILED"

        embeddings = []

        try:
            camera.warmup(seconds=1.0)

            start_time = time.time()

            while time.time() - start_time < timeout_seconds:
                frame_result = camera.read_frame()

                if not frame_result.success:
                    time.sleep(0.1)
                    continue

                detection = self.detector.detect_largest_face(frame_result.frame)

                if detection.found and detection.face_crop is not None:
                    embedding = self.embedder.extract(detection.face_crop)
                    embeddings.append(embedding)

                    if len(embeddings) >= sample_count:
                        final_embedding = average_embeddings(embeddings)
                        return final_embedding, "FACE_CAPTURED"

                    time.sleep(0.3)

                time.sleep(0.1)

            if embeddings:
                final_embedding = average_embeddings(embeddings)
                return final_embedding, "PARTIAL_FACE_CAPTURED"

            return None, "NO_FACE_DETECTED"

        finally:
            camera.release()

    def authenticate(self, username: str) -> dict:
        username = username.strip()

        if not username:
            self.database.log_auth(None, RESULT_AUTH_DENIED, 0.0, "USERNAME_REQUIRED")
            return make_response(RESULT_AUTH_DENIED, confidence=0.0, reason="USERNAME_REQUIRED")

        stored_embedding = self.database.load_embedding(username)

        if stored_embedding is None:
            self.database.log_auth(username, RESULT_AUTH_DENIED, 0.0, "USER_NOT_ENROLLED")
            return make_response(RESULT_AUTH_DENIED, confidence=0.0, reason="USER_NOT_ENROLLED")

        live_embedding, capture_reason = self.capture_live_embedding()

        if live_embedding is None:
            self.database.log_auth(username, RESULT_AUTH_DENIED, 0.0, capture_reason)
            return make_response(RESULT_AUTH_DENIED, confidence=0.0, reason=capture_reason)

        matched, confidence = is_match(
            live_embedding,
            stored_embedding,
            threshold=FaceLookConfig.CAMERA_MATCH_THRESHOLD
        )

        if matched:
            self.database.log_auth(username, RESULT_AUTH_OK, confidence, "CAMERA_FACE_MATCH")
            return make_response(RESULT_AUTH_OK, confidence=confidence, reason="CAMERA_FACE_MATCH")

        self.database.log_auth(username, RESULT_AUTH_DENIED, confidence, "CAMERA_FACE_NOT_MATCHED")
        return make_response(
            RESULT_AUTH_DENIED,
            confidence=confidence,
            reason="CAMERA_FACE_NOT_MATCHED"
        )


class CameraLivenessFaceEngine(CameraFaceEngine):
    """
    Phase 3 camera + liveness engine.

    Flow:
    1. Check liveness by detecting natural face movement
    2. If liveness passes, capture live face embedding
    3. Compare against encrypted stored embedding
    """

    def authenticate(self, username: str) -> dict:
        username = username.strip()

        if not username:
            self.database.log_auth(None, RESULT_AUTH_DENIED, 0.0, "USERNAME_REQUIRED")
            return make_response(RESULT_AUTH_DENIED, confidence=0.0, reason="USERNAME_REQUIRED")

        stored_embedding = self.database.load_embedding(username)

        if stored_embedding is None:
            self.database.log_auth(username, RESULT_AUTH_DENIED, 0.0, "USER_NOT_ENROLLED")
            return make_response(RESULT_AUTH_DENIED, confidence=0.0, reason="USER_NOT_ENROLLED")

        liveness = BasicMotionLivenessDetector(
            camera_index=0,
            timeout_seconds=6.0,
            min_horizontal_movement_ratio=0.08,
            min_samples=8,
        )

        live_ok, live_reason = liveness.check()

        if not live_ok:
            self.database.log_auth(username, RESULT_AUTH_DENIED, 0.0, live_reason)
            return make_response(
                RESULT_AUTH_DENIED,
                confidence=0.0,
                reason=live_reason
            )

        live_embedding, capture_reason = self.capture_live_embedding()

        if live_embedding is None:
            self.database.log_auth(username, RESULT_AUTH_DENIED, 0.0, capture_reason)
            return make_response(
                RESULT_AUTH_DENIED,
                confidence=0.0,
                reason=capture_reason
            )

        matched, confidence = is_match(
            live_embedding,
            stored_embedding,
            threshold=FaceLookConfig.CAMERA_MATCH_THRESHOLD
        )

        if matched:
            self.database.log_auth(username, RESULT_AUTH_OK, confidence, "LIVENESS_AND_CAMERA_FACE_MATCH")
            return make_response(
                RESULT_AUTH_OK,
                confidence=confidence,
                reason="LIVENESS_AND_CAMERA_FACE_MATCH"
            )

        self.database.log_auth(username, RESULT_AUTH_DENIED, confidence, "LIVENESS_OK_FACE_NOT_MATCHED")
        return make_response(
            RESULT_AUTH_DENIED,
            confidence=confidence,
            reason="LIVENESS_OK_FACE_NOT_MATCHED"
        )