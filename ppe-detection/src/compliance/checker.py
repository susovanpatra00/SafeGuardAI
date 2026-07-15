"""
checker.py
----------
Given a person box and the PPE items already matched to them (via
person_matcher.py), determines whether that person is COMPLIANT —
i.e. all classes marked required_for_compliance: true in
active_classes.yaml were found on them.

This reads directly from active_classes.yaml, so toggling a class's
required_for_compliance flag (or its active flag) changes compliance
logic immediately, with no code changes needed.
"""

from dataclasses import dataclass, field

import yaml

from src.inference.person_matcher import Box


@dataclass
class ComplianceResult:
    compliant: bool
    required: list[str]
    detected: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def load_required_classes(config_path: str = "data/active_classes.yaml") -> list[str]:
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)
    classes = cfg["classes"]
    return [
        name for name, meta in classes.items()
        if meta.get("active") and meta.get("required_for_compliance")
    ]


def check_compliance(matched_items: list[Box], required_classes: list[str]) -> ComplianceResult:
    """
    matched_items: PPE item boxes already assigned to this specific person
                   (output of person_matcher.match_items_to_people, for one
                   person index)
    required_classes: list of canonical class names that must be present,
                       e.g. ['helmet', 'vest', 'boots']
    """
    detected_classes = {item.class_name for item in matched_items}
    missing = [c for c in required_classes if c not in detected_classes]

    return ComplianceResult(
        compliant=(len(missing) == 0),
        required=required_classes,
        detected=sorted(detected_classes),
        missing=missing,
    )


def check_all_people(
    person_boxes: list[Box],
    assignments: dict[int, list[Box]],
    required_classes: list[str],
) -> list[ComplianceResult]:
    """
    Runs check_compliance for every detected person, in the same order
    as person_boxes, so results[i] corresponds to person_boxes[i].
    """
    return [
        check_compliance(assignments.get(i, []), required_classes)
        for i in range(len(person_boxes))
    ]