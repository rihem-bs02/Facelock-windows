import argparse
import sys

import cv2

from facelook.camera import CameraManager
from facelook.config import FaceLookConfig
from facelook.crypto_store import CryptoStore
from facelook.database import BiometricDatabase
from facelook.embedding import SimpleFaceEmbedder
from facelook.face_detector import FaceDetector


def main() -> int:
    parser = argparse.ArgumentParser(description="FACELOOK camera enrollment")
    parser.add_argument("username", help="Username to enroll")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")

    args = parser.parse_args()

    username = args.username.strip()

    if not username:
        print("[FACELOOK] ERROR: username is required.")
        return 1

    camera = CameraManager(camera_index=args.camera)

    if not camera.open():
        print("[FACELOOK] ERROR: could not open camera.")
        return 1

    detector = FaceDetector()
    embedder = SimpleFaceEmbedder()

    print("[FACELOOK] Camera enrollment started.")
    print("[FACELOOK] Put your face in front of the camera.")
    print("[FACELOOK] Press E to enroll when a face is detected.")
    print("[FACELOOK] Press Q to quit.")

    enrolled = False

    try:
        camera.warmup()

        while True:
            frame_result = camera.read_frame()

            if not frame_result.success:
                print(f"[FACELOOK] ERROR: {frame_result.message}")
                break

            frame = frame_result.frame
            detection = detector.detect_largest_face(frame)

            if detection.found and detection.box is not None:
                x, y, w, h = detection.box

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    "Face detected - Press E to enroll",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
            else:
                cv2.putText(
                    frame,
                    "No face detected",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )

            cv2.imshow("FACELOOK Camera Enrollment", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if key == ord("e"):
                if not detection.found or detection.face_crop is None:
                    print("[FACELOOK] No face detected. Cannot enroll.")
                    continue

                embedding = embedder.extract(detection.face_crop)

                crypto = CryptoStore(FaceLookConfig.KEY_PATH)
                database = BiometricDatabase(FaceLookConfig.DATABASE_PATH, crypto)
                database.save_embedding(username, embedding)

                print(f"[FACELOOK] Camera biometric profile enrolled for user: {username}")
                print("[FACELOOK] Stored encrypted embedding only. No raw image stored.")

                enrolled = True
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    if not enrolled:
        print("[FACELOOK] Enrollment cancelled.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())