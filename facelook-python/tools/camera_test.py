import argparse
import sys

import cv2

from facelook.camera import CameraManager


def main() -> int:
    parser = argparse.ArgumentParser(description="FACELOOK camera test")
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera index. Default is 0."
    )

    args = parser.parse_args()

    camera = CameraManager(camera_index=args.camera)

    if not camera.open():
        print("[FACELOOK] ERROR: Could not open camera.")
        print("[FACELOOK] Try another camera index:")
        print("python -m tools.camera_test --camera 1")
        return 1

    print("[FACELOOK] Camera opened successfully.")
    print("[FACELOOK] Press Q to quit.")

    camera.warmup()

    while True:
        result = camera.read_frame()

        if not result.success:
            print(f"[FACELOOK] ERROR: {result.message}")
            break

        frame = result.frame

        cv2.putText(
            frame,
            "FACELOOK Camera Test - Press Q to quit",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.imshow("FACELOOK Camera Test", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()

    print("[FACELOOK] Camera test finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())