"""
scripts/test_face_analyzer.py

Standalone sanity check. Run this first, before building anything else.

Usage:
    python scripts/test_face_analyzer.py --image data/test_images/sample1.jpg

What it checks:
  1. InsightFace loads and initializes on GPU without errors.
  2. It can detect faces in a real image.
  3. It produces embeddings for each detected face.
  4. Draws + saves an annotated image so you can visually confirm boxes are correct.
"""

import argparse
import cv2
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from core.face_analyzer import FaceAnalyzer  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Path to a test image with at least one face")
    parser.add_argument("--gpu", action="store_true", default=True, help="Use GPU (default: True)")
    parser.add_argument("--cpu", dest="gpu", action="store_false", help="Force CPU instead")
    parser.add_argument("--output", default="data/test_images/annotated_output.jpg")
    args = parser.parse_args()

    print(f"Loading InsightFace (gpu={args.gpu})...")
    analyzer = FaceAnalyzer(gpu=args.gpu)
    print("Model loaded successfully.\n")

    image = cv2.imread(args.image)
    if image is None:
        print(f"ERROR: could not read image at {args.image}")
        return

    print(f"Running detection + embedding on {args.image}...")
    faces = analyzer.analyze(image)

    if not faces:
        print("No faces detected. Try a clearer, front-facing test image.")
        return

    print(f"\nDetected {len(faces)} face(s):\n")
    for i, face in enumerate(faces):
        x1, y1, x2, y2 = face.bbox.astype(int)
        print(f"  Face {i+1}:")
        print(f"    bbox: ({x1}, {y1}) -> ({x2}, {y2})")
        print(f"    detection confidence: {face.det_score:.3f}")
        print(f"    embedding shape: {face.embedding.shape}")
        print(f"    raw embedding norm (expected ~20-25, not 1.0): {(face.embedding ** 2).sum() ** 0.5:.4f}")
        print(f"    normed embedding norm (should be ~1.0): {(face.normed_embedding ** 2).sum() ** 0.5:.4f}")
        if hasattr(face, "age"):
            print(f"    estimated age: {face.age}, gender: {'M' if face.gender == 1 else 'F'}")

        # draw box + index label on the image
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(image, f"#{i+1} ({face.det_score:.2f})", (x1, max(y1 - 10, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        print()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    cv2.imwrite(args.output, image)
    print(f"Annotated image saved to: {args.output}")

    # bonus: if there are 2+ faces, show similarity between first two
    # (sanity check that cosine_similarity works -- unrelated faces should score low)
    if len(faces) >= 2:
        sim = FaceAnalyzer.cosine_similarity(faces[0].normed_embedding, faces[1].normed_embedding)
        print(f"\nCosine similarity between face #1 and #2: {sim:.4f}")
        print("(Same person across two photos should typically score > 0.4-0.5;")
        print(" different people typically score lower.)")


if __name__ == "__main__":
    main()