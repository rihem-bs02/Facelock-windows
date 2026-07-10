import cv2
import time
from dataclasses import dataclass


@dataclass
class CameraFrame:
    success: bool
    frame: object | None
    message: str


class CameraManager:
    """
    Camera manager for FACELOOK.

    Phase goal:
    - open webcam
    - capture frames
    - preview camera
    - prepare for face detection later

    Important:
    - this file does not store raw images
    - frames are used only in memory
    """

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.capture = None

    def open(self) -> bool:
        self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

        if not self.capture.isOpened():
            self.capture = cv2.VideoCapture(self.camera_index)

        if not self.capture.isOpened():
            return False

        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        return True

    def read_frame(self) -> CameraFrame:
        if self.capture is None:
            return CameraFrame(False, None, "Camera is not opened")

        success, frame = self.capture.read()

        if not success or frame is None:
            return CameraFrame(False, None, "Failed to read frame")

        return CameraFrame(True, frame, "Frame captured")

    def warmup(self, seconds: float = 1.0) -> None:
        start = time.time()

        while time.time() - start < seconds:
            if self.capture is not None:
                self.capture.read()

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None