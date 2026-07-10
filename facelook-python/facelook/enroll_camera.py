import argparse
import sys
import time

import cv2

from facelook.camera import CameraManager
from facelook.config import FaceLookConfig
from facelook.crypto_store import CryptoStore
from facelook.database import BiometricDatabase
from facelook.embedding import SimpleFaceEmbedder
from facelook.embedding_utils import average_embeddings
from facelook.face_detector import FaceDetector


def main() -> int:
    parser = argparse.ArgumentParser(description="FACELOOK camera enrollment")
    parser.add_argument("username", help="Username to enroll")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument(
        "--samples",
        type=int,
        default=FaceLookConfig.ENROLLMENT_SAMPLE_COUNT,
        help="Number of face samples to capture"
    )

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

    embeddings = []

    print("[FACELOOK] Camera enrollment started.")
    print("[FACELOOK] Put your face in front of the camera.")
    print(f"[FACELOOK] Need {args.samples} good face samples.")
    print("[FACELOOK] Press C to capture a sample when face is detected.")
    print("[FACELOOK] Press Q to quit.")

    try:
        camera.warmup()

        while len(embeddings) < args.samples:
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

                status = f"Face detected - samples {len(embeddings)}/{args.samples} - Press C"
                color = (0, 255, 0)
            else:
                status = f"No face detected - samples {len(embeddings)}/{args.samples}"
                color = (0, 0, 255)

            cv2.putText(
                frame,
                status,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2
            )

            cv2.imshow("FACELOOK Camera Enrollment", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                print("[FACELOOK] Enrollment cancelled.")
                return 1

            if key == ord("c"):
                if not detection.found or detection.face_crop is None:
                    print("[FACELOOK] No face detected. Cannot capture sample.")
                    continue

                embedding = embedder.extract(detection.face_crop)
                embeddings.append(embedding)

                print(f"[FACELOOK] Captured sample {len(embeddings)}/{args.samples}")

                time.sleep(0.4)

        final_embedding = average_embeddings(embeddings)

        crypto = CryptoStore(FaceLookConfig.KEY_PATH)
        database = BiometricDatabase(FaceLookConfig.DATABASE_PATH, crypto)
        database.save_embedding(username, final_embedding)

        print(f"[FACELOOK] Camera biometric profile enrolled for user: {username}")
        print(f"[FACELOOK] Samples used: {len(embeddings)}")
        print("[FACELOOK] Stored encrypted averaged embedding only. No raw image stored.")

        return 0

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())