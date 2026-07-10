import cv2
import numpy as np
from dataclasses import dataclass


@dataclass
class FaceDetectionResult:
    found: bool
    face_crop: np.ndarray | None
    box: tuple[int, int, int, int] | None
    message: str


class FaceDetector:
    """
    Phase 2 simple face detector using OpenCV Haar Cascade.

    This is not production-grade face recognition.

    Purpose:
    - detect a face from a camera frame
    - extract the largest face crop
    - prepare the pipeline for later RetinaFace / MTCNN
    """

    def __init__(self):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"

        self.detector = cv2.CascadeClassifier(cascade_path)

        if self.detector.empty():
            raise RuntimeError(
                f"Could not load OpenCV Haar cascade detector from: {cascade_path}"
            )

    def detect_largest_face(self, frame: np.ndarray) -> FaceDetectionResult:
        if frame is None:
            return FaceDetectionResult(
                found=False,
                face_crop=None,
                box=None,
                message="Empty frame"
            )

        if not isinstance(frame, np.ndarray):
            return FaceDetectionResult(
                found=False,
                face_crop=None,
                box=None,
                message="Frame must be a numpy array"
            )

        if frame.size == 0:
            return FaceDetectionResult(
                found=False,
                face_crop=None,
                box=None,
                message="Frame is empty"
            )

        # Convert BGR camera frame to grayscale.
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        gray = cv2.equalizeHist(gray)

        faces = self.detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80)
        )

        if len(faces) == 0:
            return FaceDetectionResult(
                found=False,
                face_crop=None,
                box=None,
                message="No face detected"
            )

        # Select the largest detected face.
        x, y, w, h = max(faces, key=lambda box: box[2] * box[3])

        face_crop = frame[y:y + h, x:x + w]

        if face_crop.size == 0:
            return FaceDetectionResult(
                found=False,
                face_crop=None,
                box=None,
                message="Invalid face crop"
            )

        return FaceDetectionResult(
            found=True,
            face_crop=face_crop,
            box=(int(x), int(y), int(w), int(h)),
            message="Face detected"
        )