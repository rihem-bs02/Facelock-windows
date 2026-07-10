import cv2
import numpy as np
import onnxruntime as ort
from pathlib import Path

from facelook.matcher import normalize_embedding


class FaceNetEmbedder:
    """
    ONNX face embedding extractor.

    This version works without torch / torchvision.
    Recommended when using Python 3.14 on Windows.

    Input:
        face_crop: detected face image

    Output:
        normalized embedding vector
    """

    def __init__(
        self,
        model_path: str | Path = "models/arcface.onnx",
        input_size: tuple[int, int] = (112, 112),
    ):
        self.model_path = Path(model_path)
        self.input_size = input_size

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"ONNX model not found: {self.model_path}\n"
                "Put your ArcFace/FaceNet ONNX model in models/arcface.onnx"
            )

        self.session = ort.InferenceSession(
            str(self.model_path),
            providers=["CPUExecutionProvider"]
        )

        self.input_name = self.session.get_inputs()[0].name

    def _prepare_face(self, face_crop: np.ndarray) -> np.ndarray:
        if face_crop is None:
            raise ValueError("face crop is required")

        if not isinstance(face_crop, np.ndarray):
            raise TypeError("face_crop must be a numpy array")

        if face_crop.size == 0:
            raise ValueError("face crop is empty")

        if len(face_crop.shape) == 2:
            face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_GRAY2RGB)
        elif len(face_crop.shape) == 3 and face_crop.shape[2] == 3:
            face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
        else:
            raise ValueError("unsupported face crop format")

        face_rgb = cv2.resize(
            face_rgb,
            self.input_size,
            interpolation=cv2.INTER_AREA
        )

        face = face_rgb.astype(np.float32)

        # Standard ArcFace normalization
        face = (face - 127.5) / 127.5

        # HWC -> CHW
        face = np.transpose(face, (2, 0, 1))

        # CHW -> NCHW
        face = np.expand_dims(face, axis=0)

        return face.astype(np.float32)

    def extract(self, face_crop: np.ndarray) -> np.ndarray:
        input_tensor = self._prepare_face(face_crop)

        outputs = self.session.run(
            None,
            {self.input_name: input_tensor}
        )

        embedding = outputs[0].squeeze().astype(np.float32)

        return normalize_embedding(embedding)


# Compatibility:
# engine.py and enroll_camera.py already import SimpleFaceEmbedder.
# This keeps the rest of the project unchanged.
class SimpleFaceEmbedder(FaceNetEmbedder):
    pass