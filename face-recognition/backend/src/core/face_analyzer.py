"""
src/core/face_analyzer.py

Wraps InsightFace's FaceAnalysis app to give us:
- face detection (bounding boxes + landmarks)
- face embeddings (512-d ArcFace vectors) for recognition

This is the foundation everything else (matcher, pipeline, API) builds on.
"""

import numpy as np
from insightface.app import FaceAnalysis


class FaceAnalyzer:
    def __init__(self, model_name: str = "buffalo_l", gpu: bool = True, det_size=(640, 640)):
        """
        model_name: InsightFace model pack. 'buffalo_l' is the standard high-accuracy pack
                    (detection + recognition + landmarks + age/gender, all bundled).
        gpu: if True, use CUDA execution provider (falls back to CPU automatically if unavailable).
        det_size: input size for the detector. Larger = more accurate on small/far faces, slower.
        """
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if gpu else ["CPUExecutionProvider"]

        self.app = FaceAnalysis(name=model_name, providers=providers)
        # ctx_id=0 means "first GPU" when using CUDA provider; ignored for CPU provider.
        self.app.prepare(ctx_id=0 if gpu else -1, det_size=det_size)

    def analyze(self, image: np.ndarray):
        """
        image: a BGR image as a numpy array (i.e. straight from cv2.imread).

        Returns a list of detected faces. Each face object (from InsightFace) has:
          - .bbox             -> [x1, y1, x2, y2]
          - .kps              -> 5-point facial landmarks
          - .det_score        -> detection confidence
          - .embedding        -> 512-d RAW face embedding (numpy array, NOT normalized, norm ~20-25)
          - .normed_embedding -> 512-d L2-NORMALIZED embedding (norm ~1.0) -- USE THIS for matching
          - .age, .gender (bonus, comes free with buffalo_l)
        """
        faces = self.app.get(image)
        return faces

    @staticmethod
    def cosine_similarity(normed_embedding_a: np.ndarray, normed_embedding_b: np.ndarray) -> float:
        """
        IMPORTANT: pass face.normed_embedding here, NOT face.embedding.
        Once both vectors are L2-normalized, a plain dot product IS the cosine
        similarity. Range: -1 to 1, higher = more similar.
        Typical match threshold for buffalo_l is around 0.35-0.45 depending on your
        false-accept tolerance -- we'll tune this once we have real data.
        """
        return float(np.dot(normed_embedding_a, normed_embedding_b))