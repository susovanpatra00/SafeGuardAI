"""
person_matcher.py
------------------
Associates each detected PPE item (helmet, vest, boots, ...) with the
person box it most likely belongs to. This is necessary because a
detection model just gives you a flat list of boxes per frame — it does
NOT tell you which helmet belongs to which of the 3 people in the photo.

Matching strategy (configurable via active_classes.yaml -> matching:):
  1. IoU: overlap between the PPE box and the person box, relative to
     the PPE box's own area (not standard IoU union) — because a small
     helmet box sitting way above a person's bounding box top edge may
     have near-zero traditional IoU even when it's clearly "theirs".
  2. center_contains fallback: if IoU comes back 0 (common for helmets,
     which often sit just outside the person box), check whether the
     PPE box's center point falls within the person box, expanded
     slightly upward/outward to account for helmets/boots at the very
     top/bottom edge of a person's silhouette.

If multiple person boxes are candidates for the same PPE item, the
closest match (highest IoU / smallest center distance) wins — each PPE
item is assigned to exactly one person.
"""

from dataclasses import dataclass


@dataclass
class Box:
    x1: float
    y1: float
    x2: float
    y2: float
    class_name: str
    confidence: float = 1.0

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


def intersection_area(a: Box, b: Box) -> float:
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    return max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)


def overlap_ratio(item_box: Box, person_box: Box) -> float:
    """
    Fraction of the PPE item's own area that overlaps the person box.
    Using the item's area as the denominator (not standard IoU union)
    because PPE boxes are small relative to person boxes — standard IoU
    would almost always be tiny even for a correct match.
    """
    inter = intersection_area(item_box, person_box)
    if item_box.area == 0:
        return 0.0
    return inter / item_box.area


def center_in_expanded_box(item_box: Box, person_box: Box, expand_frac: float = 0.15) -> bool:
    """
    Fallback check: does the item's center point fall within the person
    box, expanded outward by expand_frac of the person box's own
    height/width? Handles helmets sitting just above the head (outside
    the strict person box) or boots just below the feet.
    """
    cx, cy = item_box.center
    w = person_box.x2 - person_box.x1
    h = person_box.y2 - person_box.y1

    ex1 = person_box.x1 - w * expand_frac
    ex2 = person_box.x2 + w * expand_frac
    ey1 = person_box.y1 - h * expand_frac
    ey2 = person_box.y2 + h * expand_frac

    return ex1 <= cx <= ex2 and ey1 <= cy <= ey2


def match_items_to_people(
    person_boxes: list[Box],
    item_boxes: list[Box],
    iou_threshold: float = 0.10,
    center_contains_fallback: bool = True,
) -> dict[int, list[Box]]:
    """
    Returns a dict mapping person index (into person_boxes) -> list of
    PPE item Boxes assigned to that person. Each item is assigned to at
    most one person (the best match); items with no matching person are
    dropped (not returned).
    """
    assignments: dict[int, list[Box]] = {i: [] for i in range(len(person_boxes))}

    for item in item_boxes:
        best_person_idx = None
        best_score = 0.0

        for idx, person in enumerate(person_boxes):
            score = overlap_ratio(item, person)
            if score > best_score:
                best_score = score
                best_person_idx = idx

        if best_person_idx is not None and best_score >= iou_threshold:
            assignments[best_person_idx].append(item)
            continue

        # Fallback: try center-containment if overlap-based matching failed
        if center_contains_fallback:
            for idx, person in enumerate(person_boxes):
                if center_in_expanded_box(item, person):
                    assignments[idx].append(item)
                    break  # first containing person wins in the fallback case

    return assignments