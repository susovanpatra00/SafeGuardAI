"""
scripts/enroll_one.py

Enrolls a SINGLE person from a photo, without touching existing enrollments.
Use this to add people one at a time (this is basically what the real
"Enroll" API endpoint will do later).

Usage:
    python scripts/enroll_one.py --name "Test Person C" --photo data/test_images/5.jpeg
"""

import argparse
import sys
import os
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.face_analyzer import FaceAnalyzer  # noqa: E402
from db.postgres import get_session, Person, Embedding  # noqa: E402
from db.faiss_index import FaceIndex  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--photo", required=True)
    args = parser.parse_args()

    print("Loading InsightFace...")
    analyzer = FaceAnalyzer(gpu=True)

    print("Loading FAISS index...")
    face_index = FaceIndex()

    image = cv2.imread(args.photo)
    if image is None:
        print(f"ERROR: could not read {args.photo}")
        return

    faces = analyzer.analyze(image)
    if not faces:
        print(f"ERROR: no face detected in {args.photo}")
        return

    face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    session = get_session()
    try:
        person = Person(name=args.name, photo_path=args.photo)
        session.add(person)
        session.flush()

        embedding_row = Embedding(
            person_id=person.id,
            faiss_index_id=person.id,
            embedding=face.normed_embedding.tolist(),
            source_photo=args.photo,
        )
        session.add(embedding_row)

        face_index.add(person.id, face.normed_embedding)

        session.commit()
        face_index.save()

        print(f"\nEnrolled: {args.name} (person_id={person.id}, det_score={face.det_score:.3f})")
        print(f"Total in FAISS index: {face_index.total_count()}")
    finally:
        session.close()


if __name__ == "__main__":
    main()