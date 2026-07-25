"""
Client: captures video (webcam / file / RTSP) and streams frames to the server
over WebSocket. Auto-reconnects if the connection drops (important for
internet/remote deployments where the network isn't always reliable).

Usage:
    python stream_client.py                          # uses config.py defaults
    python stream_client.py --server ws://1.2.3.4:8000/ws/stream --source 0
    python stream_client.py --source /path/to/video.mp4
    python stream_client.py --show                   # also show a local preview window

Install dependencies:
    pip install opencv-python websockets --break-system-packages   (Linux)
    pip install opencv-python websockets                            (Mac, in a venv)
"""

import sys
import os
import time
import json
import asyncio
import argparse
import logging

import cv2
import websockets
from websockets.exceptions import ConnectionClosed

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from protocol import make_hello, make_heartbeat  # noqa: E402

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("client")


def open_capture(source):
    """Open the video source (webcam index, file path, or RTSP URL)."""
    # int-like strings ("0", "1") mean webcam index; anything else is a path/URL
    src = int(source) if str(source).isdigit() else source
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {source}")
    return cap


def encode_frame(frame, resize_w, resize_h, jpeg_quality):
    """Resize (optional) and JPEG-encode a frame. Returns raw bytes."""
    if resize_w and resize_h:
        frame = cv2.resize(frame, (resize_w, resize_h))
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    if not ok:
        return None
    return buf.tobytes()


async def stream_loop(cap, ws, args, show_preview=False):
    """Send hello, then continuously capture + send frames + periodic heartbeats."""
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or args.resize_width or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or args.resize_height or 480
    fps = args.send_fps

    await ws.send(make_hello(args.camera_id, width, height, fps))
    log.info(f"Sent hello: camera_id={args.camera_id}, {width}x{height} @ {fps}fps target")

    frame_interval = 1.0 / fps
    last_send = 0.0
    last_heartbeat = time.time()

    is_file_source = isinstance(args.source, str) and not str(args.source).isdigit()

    while True:
        ret, frame = cap.read()
        if not ret:
            if is_file_source:
                # A file genuinely ended -- this is expected, not an error. Stop cleanly
                # instead of retrying (cap.isOpened() stays True at EOF, so we can't rely on it).
                log.info("Video file finished playing.")
                return "eof"
            else:
                # A live source (webcam/RTSP) failed to deliver a frame -- could be transient.
                log.warning("Failed to read frame from live source, will retry after a pause")
                return "retry"

        now = time.time()

        # Throttle to target FPS instead of sending every captured frame
        if now - last_send >= frame_interval:
            payload = encode_frame(frame, args.resize_width, args.resize_height, args.jpeg_quality)
            if payload is not None:
                await ws.send(payload)
                last_send = now

        if now - last_heartbeat >= args.heartbeat_interval:
            await ws.send(make_heartbeat(args.camera_id))
            last_heartbeat = now

        if show_preview:
            cv2.imshow("Client Preview (local only, not what server sees)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                log.info("Preview window closed by user, stopping client")
                break

        # yield control back to the event loop so websocket send/receive can happen
        await asyncio.sleep(0.001)


async def run_client(args):
    reconnect_delay = args.reconnect_delay

    cap = open_capture(args.source)
    log.info(f"Opened video source: {args.source}")

    connect_url = f"{args.server}?key={args.api_key}"

    try:
        while True:
            try:
                log.info(f"Connecting to {args.server} ...")
                async with websockets.connect(connect_url, max_size=None) as ws:
                    log.info("Connected.")
                    reconnect_delay = args.reconnect_delay  # reset backoff on success
                    result = await stream_loop(cap, ws, args, show_preview=args.show)

                if result == "eof":
                    # File source finished normally -- nothing to reconnect to, stop here.
                    break
                elif result == "retry":
                    # Live source hiccup -- back off before trying to read again.
                    log.info(f"Pausing {reconnect_delay}s before retrying source read...")
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, args.max_reconnect_delay)

            except (ConnectionClosed, ConnectionRefusedError, OSError) as e:
                log.warning(f"Connection lost/failed: {e}. Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, args.max_reconnect_delay)
    finally:
        cap.release()
        if args.show:
            cv2.destroyAllWindows()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--server", default=config.SERVER_URL)
    p.add_argument("--api-key", default=config.API_KEY)
    p.add_argument("--camera-id", default=config.CAMERA_ID)
    p.add_argument("--source", default=config.SOURCE)
    p.add_argument("--resize-width", type=int, default=config.RESIZE_WIDTH)
    p.add_argument("--resize-height", type=int, default=config.RESIZE_HEIGHT)
    p.add_argument("--jpeg-quality", type=int, default=config.JPEG_QUALITY)
    p.add_argument("--send-fps", type=float, default=config.SEND_FPS)
    p.add_argument("--heartbeat-interval", type=float, default=config.HEARTBEAT_INTERVAL_SEC)
    p.add_argument("--reconnect-delay", type=float, default=config.RECONNECT_DELAY_SEC)
    p.add_argument("--max-reconnect-delay", type=float, default=config.MAX_RECONNECT_DELAY_SEC)
    p.add_argument("--show", action="store_true", help="Show a local preview window")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        asyncio.run(run_client(args))
    except KeyboardInterrupt:
        log.info("Stopped by user (Ctrl+C)")