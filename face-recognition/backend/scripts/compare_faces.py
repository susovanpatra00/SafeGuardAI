"""
scripts/compare_faces.py

Compares faces ACROSS multiple separate images (not faces within one image).
Use this to sanity-check that:
  - Same person across different photos -> high similarity
  - Different people -> low similarity

Usage:
    python scripts/compare_faces.py --images data/test_images/1.jpeg data/test_images/2.jpeg data/test_images/3.jpeg
"""

import argparse
import cv2
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from core.face_analyzer import FaceAnalyzer  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", nargs="+", required=True, help="Paths to 2+ images to compare")
    args = parser.parse_args()

    print("Loading InsightFace...")
    analyzer = FaceAnalyzer(gpu=True)
    print("Model loaded.\n")

    entries = []  # (filename, normed_embedding)
    for path in args.images:
        image = cv2.imread(path)
        if image is None:
            print(f"WARNING: could not read {path}, skipping")
            continue
        faces = analyzer.analyze(image)
        if not faces:
            print(f"WARNING: no face found in {path}, skipping")
            continue
        # take the largest face if multiple are detected in one image
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        entries.append((os.path.basename(path), face.normed_embedding))
        print(f"{os.path.basename(path)}: face found, det_score={face.det_score:.3f}")

    print(f"\n{'-'*50}")
    print("Pairwise similarity matrix:")
    print(f"{'-'*50}\n")

    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            name_a, emb_a = entries[i]
            name_b, emb_b = entries[j]
            sim = FaceAnalyzer.cosine_similarity(emb_a, emb_b)
            verdict = "SAME PERSON (likely)" if sim > 0.4 else "different people (likely)"
            print(f"  {name_a}  <->  {name_b}:  similarity = {sim:.4f}   [{verdict}]")

    print(f"\n{'-'*50}")
    print("Rule of thumb for buffalo_l: >0.4-0.5 usually same person, <0.3 usually different.")
    print("We'll tune the exact production threshold once we have real enrollment data.")


if __name__ == "__main__":
    main()