import time

from facelook.camera import CameraManager
from facelook.face_detector import FaceDetector


class BasicMotionLivenessDetector:
    """
    Phase 3 basic liveness detector.

    It checks whether the detected face moves naturally across frames.

    This is NOT production-grade anti-spoofing.
    Later we replace or improve this with:
    - blink detection
    - depth / IR camera
    - texture-based anti-spoofing
    - MiniFASNet / Silent Face Anti-Spoofing
    """

    def __init__(
        self,
        camera_index: int = 0,
        timeout_seconds: float = 6.0,
        min_horizontal_movement_ratio: float = 0.08,
        min_samples: int = 8,
    ):
        self.camera_index = camera_index
        self.timeout_seconds = timeout_seconds
        self.min_horizontal_movement_ratio = min_horizontal_movement_ratio
        self.min_samples = min_samples
        self.detector = FaceDetector()

    def check(self) -> tuple[bool, str]:
        camera = CameraManager(camera_index=self.camera_index)

        if not camera.open():
            return False, "LIVENESS_CAMERA_OPEN_FAILED"

        centers: list[float] = []
        frame_width = None

        try:
            camera.warmup(seconds=1.0)

            start_time = time.time()

            while time.time() - start_time < self.timeout_seconds:
                frame_result = camera.read_frame()

                if not frame_result.success or frame_result.frame is None:
                    time.sleep(0.1)
                    continue

                frame = frame_result.frame
                frame_width = frame.shape[1]

                detection = self.detector.detect_largest_face(frame)

                if detection.found and detection.box is not None:
                    x, y, w, h = detection.box
                    center_x = x + (w / 2.0)
                    centers.append(center_x)

                time.sleep(0.15)

            if len(centers) < self.min_samples:
                return False, "LIVENESS_NOT_ENOUGH_FACE_SAMPLES"

            if frame_width is None or frame_width <= 0:
                return False, "LIVENESS_INVALID_FRAME"

            movement = max(centers) - min(centers)
            movement_ratio = movement / float(frame_width)

            if movement_ratio >= self.min_horizontal_movement_ratio:
                return True, "LIVENESS_OK"

            return False, "LIVENESS_NO_MOTION_DETECTED"

        finally:
            camera.release()