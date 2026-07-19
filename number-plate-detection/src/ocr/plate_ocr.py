"""
fast-plate-ocr wrapper specialized for reading cropped plate images.

Unlike EasyOCR (generic scene-text OCR — reads any text in any photo),
fast-plate-ocr is a purpose-built plate OCR: ONNX-based, ships pretrained
region-specific models, and was validated against real footage from this
project with 4/4 exact matches on crops EasyOCR was garbling.

Requires grayscale input (not color) — a shape mismatch otherwise.
"""

import logging
import re
from dataclasses import dataclass

import cv2
import numpy as np
from fast_plate_ocr import LicensePlateRecognizer

logger = logging.getLogger(__name__)

# Characters that commonly get confused with each other in scene-text OCR,
# specifically the digit <-> letter direction (shape-alike pairs). Kept as a
# safety net even with a plate-specialized model — cheap insurance against
# residual noise on hard crops.
DIGIT_TO_LETTER = {"0": "O", "1": "I", "5": "S", "6": "G", "8": "B", "2": "Z"}
LETTER_TO_DIGIT = {v: k for k, v in DIGIT_TO_LETTER.items()}
LETTER_TO_DIGIT.update({"L": "1", "Z": "2"})


def correct_by_format(text: str, format_positions: str) -> str:
    """
    Fix digit/letter confusions using a known fixed format string, e.g.
    "LLDDLLL" for UK plates (2 letters, 2 digits, 3 letters). Only applies
    if `text` is exactly the expected length — otherwise returns unchanged,
    since we can't confidently align positions on a length mismatch.
    """
    if not format_positions or len(text) != len(format_positions):
        return text

    corrected = []
    for ch, expected in zip(text, format_positions):
        if expected == "L" and ch in DIGIT_TO_LETTER:
            corrected.append(DIGIT_TO_LETTER[ch])
        elif expected == "D" and ch in LETTER_TO_DIGIT:
            corrected.append(LETTER_TO_DIGIT[ch])
        else:
            corrected.append(ch)
    return "".join(corrected)


def vote_plate_text(history: list[tuple[str, float]], format_positions: str | None = None) -> str | None:
    """
    Combine every OCR read a track has accumulated into one consensus
    string, instead of trusting whichever single frame scored highest
    confidence — a blurry early frame can score deceptively high and
    lock in a bad read otherwise.

    Groups reads by length (only same-length reads can be aligned
    character-by-character), picks the length with the most total
    confidence-weight behind it, then votes per character position.
    """
    if not history:
        return None

    length_weight: dict[int, float] = {}
    for text, conf in history:
        length_weight[len(text)] = length_weight.get(len(text), 0.0) + conf
    best_length = max(length_weight, key=length_weight.get)

    candidates = [(t, c) for t, c in history if len(t) == best_length]

    voted_chars = []
    for i in range(best_length):
        char_weight: dict[str, float] = {}
        for text, conf in candidates:
            char_weight[text[i]] = char_weight.get(text[i], 0.0) + conf
        voted_chars.append(max(char_weight, key=char_weight.get))
    voted = "".join(voted_chars)

    if format_positions:
        voted = correct_by_format(voted, format_positions)
    return voted


@dataclass
class OCRResult:
    text: str
    confidence: float
    is_valid_format: bool


class PlateOCR:
    def __init__(
        self,
        model_name: str = "global-plates-mobile-vit-v2-model",
        device: str = "cuda",
        min_confidence: float = 0.6,
        validation_regex: str | None = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$",
        strip_chars: str = " -.",
        format_positions: str | None = None,  # e.g. "LLDDLLL" for UK — enables
                                                 # position-aware digit/letter correction
    ):
        logger.info("Initializing fast-plate-ocr (model=%s, device=%s)", model_name, device)
        self.recognizer = LicensePlateRecognizer(hub_ocr_model=model_name, device=device)
        self.min_confidence = min_confidence
        self.validation_regex = re.compile(validation_regex) if validation_regex else None
        self.strip_chars = strip_chars
        self.format_positions = format_positions

    def _clean(self, raw_text: str) -> str:
        text = raw_text.upper()
        for ch in self.strip_chars:
            text = text.replace(ch, "")
        return text.strip()

    def validate(self, text: str) -> bool:
        if not self.validation_regex:
            return True
        return bool(self.validation_regex.match(text))

    def read(self, plate_crop: np.ndarray) -> OCRResult | None:
        if plate_crop.size == 0:
            return None

        gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY) if plate_crop.ndim == 3 else plate_crop

        results = self.recognizer.run(gray, return_confidence=True)
        if not results:
            return None

        pred = results[0]
        if not pred.plate:
            return None

        avg_conf = float(np.mean(pred.char_probs)) if pred.char_probs is not None else 1.0

        combined_text = self._clean(pred.plate)
        combined_text = correct_by_format(combined_text, self.format_positions)

        if avg_conf < self.min_confidence:
            logger.debug("OCR below confidence threshold: %s (%.2f)", combined_text, avg_conf)
            return None

        is_valid = self.validate(combined_text)

        return OCRResult(text=combined_text, confidence=avg_conf, is_valid_format=is_valid)