"""
Two-stage cascade: detect vehicles first (large, easy target even in
wide/distant shots), gate out anything too far away to have a readable
plate, then only run the (more expensive, more fragile) plate detector
on an upscaled crop of the vehicles that passed the gate.

This exists because running the plate detector directly on a full wide
-angle frame fails outright — a distant plate is a handful of pixels
after YOLO's internal resize, effectively invisible. Cropping to the
vehicle first and upscaling gives the plate detector a fighting chance.
"""

import logging
from dataclasses import dataclass

import numpy as np

from src.detector.plate_detector import Detection, PlateDetector
from src.detector.vehicle_detector import VehicleDetector
from src.pipeline.geometry import crop_and_upscale, is_close_enough, map_box_to_frame

logger = logging.getLogger(__name__)


@dataclass
class CascadeResult:
    vehicle_box: tuple[int, int, int, int]
    vehicle_confidence: float
    plate_box_in_frame: tuple[int, int, int, int] | None  # None if no plate found
    plate_confidence: float | None
    plate_crop: np.ndarray | None  # cropped plate region, ready for OCR


class DetectionCascade:
    def __init__(
        self,
        vehicle_detector: VehicleDetector,
        plate_detector: PlateDetector,
        min_vehicle_height_frac: float,
        crop_upscale_size: int,
    ):
        self.vehicle_detector = vehicle_detector
        self.plate_detector = plate_detector
        self.min_vehicle_height_frac = min_vehicle_height_frac
        self.crop_upscale_size = crop_upscale_size

    def run(self, frame: np.ndarray) -> list[CascadeResult]:
        frame_h = frame.shape[0]
        vehicle_detections = self.vehicle_detector.detect(frame)

        results = []
        for veh in vehicle_detections:
            if not is_close_enough(veh.box, frame_h, self.min_vehicle_height_frac):
                continue  # too far away, skip plate detection entirely

            crop, transform = crop_and_upscale(frame, veh.box, self.crop_upscale_size)
            if crop.size == 0:
                continue

            plate_detections = self.plate_detector.detect(crop)
            if not plate_detections:
                results.append(
                    CascadeResult(
                        vehicle_box=veh.box,
                        vehicle_confidence=veh.confidence,
                        plate_box_in_frame=None,
                        plate_confidence=None,
                        plate_crop=None,
                    )
                )
                continue

            # take the highest-confidence plate detection in this crop
            best_plate = max(plate_detections, key=lambda d: d.confidence)
            plate_box_frame = map_box_to_frame(best_plate.box, transform)
            plate_crop = PlateDetector.crop(crop, best_plate)

            results.append(
                CascadeResult(
                    vehicle_box=veh.box,
                    vehicle_confidence=veh.confidence,
                    plate_box_in_frame=plate_box_frame,
                    plate_confidence=best_plate.confidence,
                    plate_crop=plate_crop,
                )
            )

        return results
