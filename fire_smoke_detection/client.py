"""
client.py
---------
Runs on your local machine (e.g. Mac). Captures the webcam, streams
each frame to the detection server over WebSocket, and overlays the
server's response live: bounding boxes plus a big "FIRE DETECTED" /
"SMOKE DETECTED" banner when relevant.

Usage:

    python client.py --server ws://<server-ip>:8765

    python client.py --server ws://<server-ip>:8765 --camera 0 --quality 80

Press 'q' in the video window to quit.
"""

import argparse
import asyncio
import json
import time

import cv2
import websockets

BOX_COLORS = {
    "fire": (0, 0, 255),      # red (BGR)
    "smoke": (0, 165, 255),   # orange (BGR)
}
DEFAULT_BOX_COLOR = (0, 255, 0)

BANNER_FIRE = {"text": "FIRE DETECTED", "bg": (0, 0, 200), "fg": (255, 255, 255)}
BANNER_SMOKE = {"text": "SMOKE DETECTED", "bg": (0, 140, 255), "fg": (0, 0, 0)}


def draw_boxes(frame, detections):
    for d in detections:
        x1, y1, x2, y2 = (int(v) for v in d["box"])
        color = BOX_COLORS.get(d["label"].lower(), DEFAULT_BOX_COLOR)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label_text = f'{d["label"]} {d["conf"]:.2f}'
        cv2.putText(frame, label_text, (x1, max(0, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)


def draw_banner(frame, banner):
    h, w = frame.shape[:2]
    bar_height = max(40, h // 12)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, bar_height), banner["bg"], -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    text = banner["text"]
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = bar_height / 45.0
    thickness = 2
    (text_w, text_h), _ = cv2.getTextSize(text, font, scale, thickness)
    x = (w - text_w) // 2
    y = (bar_height + text_h) // 2
    cv2.putText(frame, text, (x, y), font, scale, banner["fg"], thickness, cv2.LINE_AA)


def draw_status(frame, fps, infer_ms):
    h = frame.shape[0]
    text = f"{fps:.1f} fps | server infer {infer_ms:.0f} ms"
    cv2.putText(frame, text, (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (200, 200, 200), 1, cv2.LINE_AA)


async def stream(server_uri: str, camera_index, quality: int, width, height):
    cap = cv2.VideoCapture(camera_index)
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera index {camera_index}")

    print(f"Connecting to {server_uri} ...")
    async with websockets.connect(server_uri, max_size=20 * 1024 * 1024) as ws:
        print("Connected. Press 'q' in the video window to quit.")
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]

        t_prev = time.time()
        fps = 0.0
        infer_ms = 0.0

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Camera read failed, stopping.")
                break

            ok, buf = cv2.imencode(".jpg", frame, encode_params)
            if not ok:
                continue

            await ws.send(buf.tobytes())
            response = await ws.recv()
            result = json.loads(response)

            infer_ms = result.get("infer_ms", infer_ms)
            draw_boxes(frame, result.get("detections", []))

            if result.get("fire"):
                draw_banner(frame, BANNER_FIRE)
            elif result.get("smoke"):
                draw_banner(frame, BANNER_SMOKE)

            t_now = time.time()
            fps = 1.0 / max(t_now - t_prev, 1e-6)
            t_prev = t_now
            draw_status(frame, fps, infer_ms)

            cv2.imshow("Live Fire/Smoke Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()


def parse_args():
    parser = argparse.ArgumentParser(description="Stream webcam to the smoke/fire detection server.")
    parser.add_argument("--server", type=str, required=True,
                        help="WebSocket URL of the server, e.g. ws://192.168.1.20:8765")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default 0).")
    parser.add_argument("--quality", type=int, default=80, help="JPEG quality sent to server (1-100).")
    parser.add_argument("--width", type=int, default=None, help="Request a specific capture width.")
    parser.add_argument("--height", type=int, default=None, help="Request a specific capture height.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(stream(args.server, args.camera, args.quality, args.width, args.height))