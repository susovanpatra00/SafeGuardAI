"""
Test client: sends synthetic generated frames to the server. No webcam or
video file needed -- useful for testing the server (locally or on a remote
box with no camera attached) and for verifying the perimeter/alert logic
by making a moving box cross into the zone on a schedule.

Usage:
    python test_client.py
    python test_client.py --server ws://1.2.3.4:8000/ws/stream --camera-id test_cam_02
    python test_client.py --frames 50          # send 50 frames then stop (default: run forever)
    python test_client.py --trigger-breach     # periodically draw the moving box crossing
                                                # into the bottom-right quadrant, useful for
                                                # testing alert logic once the perimeter zone
                                                # is set up there

Install dependencies:
    pip install opencv-python websockets numpy --break-system-packages   (Linux)
    pip install opencv-python websockets numpy                            (Mac, in a venv)
"""

import sys
import os
import time
import asyncio
import argparse
import logging

import cv2
import numpy as np
import websockets
from websockets.exceptions import ConnectionClosed

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from protocol import make_hello, make_heartbeat  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("test_client")

WIDTH, HEIGHT = 640, 480


def generate_frame(frame_num: int, trigger_breach: bool) -> np.ndarray:
    """
    Build a synthetic frame: dark background, a timestamp, and a moving
    white box that bounces around (simulating a moving object for
    background-subtraction detectors to pick up).
    """
    frame = np.full((HEIGHT, WIDTH, 3), 30, dtype=np.uint8)  # dark gray background

    # Moving box position -- bounces left/right across the frame
    box_w, box_h = 60, 60
    period = 100  # frames per full sweep
    t = (frame_num % period) / period
    # triangle wave 0->1->0 for a back-and-forth motion
    sweep = t * 2 if t < 0.5 else 2 - t * 2

    if trigger_breach:
        # keep the box confined to bottom-right quadrant so it's easy to
        # place a test perimeter zone there and reliably trigger it
        x = int(WIDTH * 0.6 + sweep * WIDTH * 0.3)
        y = int(HEIGHT * 0.6 + sweep * HEIGHT * 0.3)
    else:
        x = int(sweep * (WIDTH - box_w))
        y = HEIGHT // 2 - box_h // 2

    cv2.rectangle(frame, (x, y), (x + box_w, y + box_h), (255, 255, 255), -1)

    cv2.putText(frame, f"frame {frame_num}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(frame, time.strftime("%H:%M:%S"), (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    return frame


def encode_frame(frame, jpeg_quality=70):
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    return buf.tobytes() if ok else None


async def run_test_client(args):
    frame_num = 0
    frame_interval = 1.0 / args.fps
    reconnect_delay = 2.0
    connect_url = f"{args.server}?key={args.api_key}"

    while True:
        try:
            log.info(f"Connecting to {args.server} ...")
            async with websockets.connect(connect_url, max_size=None) as ws:
                log.info("Connected. Sending synthetic frames...")
                reconnect_delay = 2.0

                await ws.send(make_hello(args.camera_id, WIDTH, HEIGHT, args.fps))
                last_heartbeat = time.time()

                while args.frames == 0 or frame_num < args.frames:
                    frame = generate_frame(frame_num, args.trigger_breach)
                    payload = encode_frame(frame, args.jpeg_quality)
                    if payload:
                        await ws.send(payload)

                    if args.show:
                        cv2.imshow("Test Client (synthetic frames being sent)", frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            log.info("Preview closed by user, stopping.")
                            return

                    frame_num += 1

                    now = time.time()
                    if now - last_heartbeat >= 10:
                        await ws.send(make_heartbeat(args.camera_id))
                        last_heartbeat = now

                    await asyncio.sleep(frame_interval)

                log.info(f"Sent {frame_num} frames total, stopping (--frames limit reached).")
                return

        except (ConnectionClosed, ConnectionRefusedError, OSError) as e:
            log.warning(f"Connection lost/failed: {e}. Reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 30)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--server", default="ws://127.0.0.1:8000/ws/stream")
    p.add_argument("--api-key", default="CHANGE_ME_TO_MATCH_SERVER")
    p.add_argument("--camera-id", default="test_cam_synthetic")
    p.add_argument("--fps", type=float, default=10)
    p.add_argument("--jpeg-quality", type=int, default=70)
    p.add_argument("--frames", type=int, default=0, help="Stop after N frames (0 = run forever)")
    p.add_argument("--trigger-breach", action="store_true",
                    help="Confine the moving box to the bottom-right quadrant, for testing a zone placed there")
    p.add_argument("--show", action="store_true", help="Show a local preview window of what's being sent")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(run_test_client(args))
    except KeyboardInterrupt:
        log.info("Stopped by user (Ctrl+C)")
    finally:
        cv2.destroyAllWindows()