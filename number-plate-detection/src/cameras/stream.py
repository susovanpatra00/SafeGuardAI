"""
RTSP frame ingestion with auto-reconnect.

Runs the capture loop in a background thread and always exposes the
*latest* frame — this avoids the classic OpenCV RTSP buffering lag where
you fall further and further behind real-time.
"""

import logging
import threading
import time
from dataclasses import dataclass

import cv2

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    rtsp_url: str
    reconnect_delay_sec: int = 5
    target_width: int | None = 1280


class RTSPStream:
    def __init__(self, config: StreamConfig):
        self.config = config
        self._cap: cv2.VideoCapture | None = None
        self._latest_frame = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("RTSP capture thread started for %s", self.config.rtsp_url)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._cap:
            self._cap.release()

    def _open(self) -> bool:
        self._cap = cv2.VideoCapture(self.config.rtsp_url, cv2.CAP_FFMPEG)
        # keep internal buffer small so we don't drift behind live
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return self._cap.isOpened()

    def _capture_loop(self):
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                logger.warning("Stream not open, (re)connecting...")
                if not self._open():
                    logger.error(
                        "Failed to open RTSP stream, retrying in %ss",
                        self.config.reconnect_delay_sec,
                    )
                    time.sleep(self.config.reconnect_delay_sec)
                    continue

            ok, frame = self._cap.read()
            if not ok:
                logger.warning("Frame read failed, will attempt reconnect")
                self._cap.release()
                self._cap = None
                time.sleep(self.config.reconnect_delay_sec)
                continue

            if self.config.target_width and frame.shape[1] != self.config.target_width:
                scale = self.config.target_width / frame.shape[1]
                frame = cv2.resize(
                    frame,
                    (self.config.target_width, int(frame.shape[0] * scale)),
                )

            with self._lock:
                self._latest_frame = frame

    def read(self):
        """Return the most recent frame, or None if nothing captured yet."""
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()
