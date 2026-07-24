"""
scripts/test_enrollment.py

End-to-end sanity check for the full enrollment + matching pipeline:
  1. Detect + embed a face from a photo (InsightFace)
  2. Store the person + embedding in Postgres
  3. Add the embedding to FAISS
  4. Search a NEW photo against the FAISS index and confirm it matches the right person

Usage:
    python scripts/test_enrollment.py

Edit ENROLL_PHOTOS below to point at your real test images.
"""

import sys
import os
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.face_analyzer import FaceAnalyzer  # noqa: E402
from db.postgres import get_session, init_db, Person, Embedding  # noqa: E402
from db.faiss_index import FaceIndex  # noqa: E402

# EDIT THESE: map a name -> photo path for enrollment.
# Use photos of DIFFERENT people here (e.g. your 2.jpeg, 3.jpeg from before).
ENROLL_PHOTOS = {
    "Test Person A": "data/test_images/1.jpeg",
    "Test Person B": "data/test_images/3.jpeg",
}

# EDIT THIS: a photo of one of the enrolled people, taken from a DIFFERENT photo
# than the one used to enroll them (e.g. if 1.jpeg and 4.jpeg are the same person,
# and you enrolled with 1.jpeg under a different flow, search with 4.jpeg).
SEARCH_PHOTO = "data/test_images/4.jpeg"


def main():
    print("Initializing DB tables (safe to run repeatedly)...")
    init_db()

    print("Loading InsightFace...")
    analyzer = FaceAnalyzer(gpu=True)

    print("Loading FAISS index...")
    face_index = FaceIndex()

    session = get_session()

    print(f"\n{'='*50}\nENROLLING {len(ENROLL_PHOTOS)} PEOPLE\n{'='*50}")
    for name, photo_path in ENROLL_PHOTOS.items():
        image = cv2.imread(photo_path)
        if image is None:
            print(f"  SKIP {name}: could not read {photo_path}")
            continue

        faces = analyzer.analyze(image)
        if not faces:
            print(f"  SKIP {name}: no face detected in {photo_path}")
            continue

        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

        # 1. Create the person record
        person = Person(name=name, photo_path=photo_path)
        session.add(person)
        session.flush()  # get person.id without fully committing yet

        # 2. Use person.id as the faiss_index_id too (simple 1:1 mapping for now)
        embedding_row = Embedding(
            person_id=person.id,
            faiss_index_id=person.id,
            embedding=face.normed_embedding.tolist(),
            source_photo=photo_path,
        )
        session.add(embedding_row)

        # 3. Add to FAISS
        face_index.add(person.id, face.normed_embedding)

        print(f"  Enrolled: {name} (person_id={person.id}, det_score={face.det_score:.3f})")

    session.commit()
    face_index.save()
    print(f"\nTotal in FAISS index: {face_index.total_count()}")

    print(f"\n{'='*50}\nSEARCHING: {SEARCH_PHOTO}\n{'='*50}")
    query_image = cv2.imread(SEARCH_PHOTO)
    if query_image is None:
        print(f"Could not read {SEARCH_PHOTO}")
        return

    query_faces = analyzer.analyze(query_image)
    if not query_faces:
        print("No face detected in search photo.")
        return

    query_face = max(query_faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    results = face_index.search(query_face.normed_embedding, top_k=3)

    if not results:
        print("No matches found in index.")
        return

    print("\nTop matches:")
    for faiss_id, score in results:
        person = session.query(Person).filter(Person.id == faiss_id).first()
        name = person.name if person else "UNKNOWN (not in DB)"
        verdict = "MATCH" if score > 0.4 else "no match (below threshold)"
        print(f"  {name}: similarity={score:.4f}  [{verdict}]")

    session.close()


if __name__ == "__main__":
    main()