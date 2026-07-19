"""
PaddleOCR wrapper specialized for reading cropped plate images.

PaddleOCR returns line-level text + confidence; plates are usually a
single line (or two, for stacked-format plates), so we concatenate all
detected text fragments, strip noise characters, then run it through a
regex validator to catch obvious misreads.
"""

import logging
import re
from dataclasses import dataclass

import numpy as np
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    text: str
    confidence: float
    is_valid_format: bool


class PlateOCR:
    def __init__(
        self,
        lang: str = "en",
        use_angle_cls: bool = True,
        min_confidence: float = 0.6,
        validation_regex: str | None = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$",
        strip_chars: str = " -.",
    ):
        logger.info("Initializing PaddleOCR (lang=%s)", lang)
        self.ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang, show_log=False)
        self.min_confidence = min_confidence
        self.validation_regex = re.compile(validation_regex) if validation_regex else None
        self.strip_chars = strip_chars

    def _clean(self, raw_text: str) -> str:
        text = raw_text.upper()
        for ch in self.strip_chars:
            text = text.replace(ch, "")
        # common OCR confusions on plates: O/0, I/1 — only fix in digit-heavy
        # positions if you find it helps your specific dataset; left as a
        # no-op here so you can tune per-region without surprises.
        return text.strip()

    def read(self, plate_crop: np.ndarray) -> OCRResult | None:
        if plate_crop.size == 0:
            return None

        result = self.ocr.ocr(plate_crop, cls=True)
        if not result or not result[0]:
            return None

        fragments = []
        confidences = []
        for line in result[0]:
            text, conf = line[1]
            fragments.append(text)
            confidences.append(conf)

        combined_text = self._clean("".join(fragments))
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        if avg_conf < self.min_confidence:
            logger.debug("OCR below confidence threshold: %s (%.2f)", combined_text, avg_conf)
            return None

        is_valid = bool(self.validation_regex.match(combined_text)) if self.validation_regex else True

        return OCRResult(text=combined_text, confidence=avg_conf, is_valid_format=is_valid)
