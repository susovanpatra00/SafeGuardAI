"""
src/core/matcher.py

Ties together FAISS (fast vector search) and Postgres (person metadata)
into a single clean interface: "given a face embedding, who is this?"

This is the one place the match threshold lives, so it's easy to tune later
without hunting through the pipeline code.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional

from db.faiss_index import FaceIndex
from db.postgres import get_session, Person

# Tuned from our real test data: same-person pairs scored ~0.70, different-people
# pairs scored -0.04 to 0.03. 0.40 sits comfortably in the gap between them.
# Revisit this once you have more enrolled people and real-world footage --
# lighting/angle/camera quality can shift the gap.
DEFAULT_MATCH_THRESHOLD = 0.40


@dataclass
class MatchResult:
    is_known: bool
    person_id: Optional[int]
    person_name: Optional[str]
    confidence: float  # cosine similarity of the best match, regardless of is_known


class FaceMatcher:
    def __init__(self, threshold: float = DEFAULT_MATCH_THRESHOLD):
        self.threshold = threshold
        self.face_index = FaceIndex()

    def match(self, normed_embedding: np.ndarray) -> MatchResult:
        """
        Searches the FAISS index for the closest enrolled person.
        Returns a MatchResult -- is_known=False means either no enrolled faces
        exist yet, or the best match scored below the threshold (i.e. "Unknown").
        """
        results = self.face_index.search(normed_embedding, top_k=1)

        if not results:
            return MatchResult(is_known=False, person_id=None, person_name=None, confidence=0.0)

        best_faiss_id, best_score = results[0]

        if best_score < self.threshold:
            return MatchResult(is_known=False, person_id=None, person_name=None, confidence=best_score)

        session = get_session()
        try:
            person = session.query(Person).filter(Person.id == best_faiss_id).first()
            if person is None:
                # embedding exists in FAISS but the person record is gone (deleted?) --
                # treat as unknown rather than crashing.
                return MatchResult(is_known=False, person_id=None, person_name=None, confidence=best_score)
            return MatchResult(is_known=True, person_id=person.id, person_name=person.name, confidence=best_score)
        finally:
            session.close()