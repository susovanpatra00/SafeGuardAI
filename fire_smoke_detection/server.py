"""
server.py
---------
Hosts the trained smoke/fire YOLO model and serves live inference over
a WebSocket. A client (e.g. your Mac, see client.py) streams webcam
JPEG frames to this server; for each frame the server runs detection
and replies with a small JSON payload describing what it found.

Run on the machine with the GPU / model weights:

    python server.py --weights runs/detect/models/trained/20260715_0724_smoke-fire/weights/best.pt --host 0.0.0.0 --port 8770

Then point client.py at ws://<this-machine-ip>:8765

Config precedence mirrors detect.py: values in configs/inference_config.yaml
are used as defaults, CLI flags override them.
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

import cv2
import numpy as np
import yaml
import websockets
from websockets.server import WebSocketServerProtocol
from ultralytics import YOLO

# Labels that trigger each banner client-side. Adjust if your model's
# class names differ (check model.names after loading, printed at startup).
FIRE_LABELS = {"fire"}
SMOKE_LABELS = {"smoke"}


def load_config(config_path: Path) -> dict:
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


class DetectionServer:
    def __init__(self, weights: Path, conf: float, iou: float, imgsz: int, device):
        if not weights.exists():
            raise FileNotFoundError(
                f"Weights not found at {weights}.\n"
                f"Set --weights or update `weights:` in the config file."
            )
        print(f"Loading model: {weights}")
        self.model = YOLO(str(weights))
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.device = device
        print(f"Model classes: {self.model.names}")
        print(f"conf={conf}  iou={iou}  imgsz={imgsz}  device={device}")

    def infer(self, frame: np.ndarray) -> dict:
        results = self.model.predict(
            source=frame,
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            device=self.device,
            save=False,
            verbose=False,
            stream=False,
        )
        r = results[0]
        names = self.model.names

        detections = []
        fire = False
        smoke = False
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = names[cls_id]
            score = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append({
                "label": label,
                "conf": round(score, 3),
                "box": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
            })
            label_lower = label.lower()
            if label_lower in FIRE_LABELS:
                fire = True
            if label_lower in SMOKE_LABELS:
                smoke = True

        return {"fire": fire, "smoke": smoke, "detections": detections}


async def handle_client(websocket: WebSocketServerProtocol, server: DetectionServer):
    peer = websocket.remote_address
    print(f"Client connected: {peer}")
    frame_count = 0
    t_start = time.time()
    try:
        async for message in websocket:
            if not isinstance(message, (bytes, bytearray)):
                continue  # ignore anything that isn't a JPEG frame

            arr = np.frombuffer(message, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            t0 = time.time()
            result = server.infer(frame)
            result["infer_ms"] = round((time.time() - t0) * 1000, 1)

            await websocket.send(json.dumps(result))

            frame_count += 1
            if frame_count % 60 == 0:
                fps = frame_count / (time.time() - t_start)
                print(f"[{peer}] {frame_count} frames processed, ~{fps:.1f} fps")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        print(f"Client disconnected: {peer}")


async def main(args):
    cfg = load_config(args.config)
    weights = Path(args.weights or cfg.get("weights", ""))
    conf = args.conf if args.conf is not None else cfg.get("conf", 0.25)
    iou = args.iou if args.iou is not None else cfg.get("iou", 0.45)
    imgsz = args.imgsz if args.imgsz is not None else cfg.get("imgsz", 640)
    device = args.device if args.device is not None else cfg.get("device", None)

    server = DetectionServer(weights, conf, iou, imgsz, device)

    print(f"Starting WebSocket server on ws://{args.host}:{args.port}")
    async with websockets.serve(
        lambda ws: handle_client(ws, server),
        args.host,
        args.port,
        max_size=20 * 1024 * 1024,  # allow large JPEG frames
        ping_interval=20,
        ping_timeout=20,
    ):
        await asyncio.Future()  # run forever


def parse_args():
    parser = argparse.ArgumentParser(description="Live smoke/fire detection WebSocket server.")
    parser.add_argument("--config", type=Path, default=Path("configs/inference_config.yaml"))
    parser.add_argument("--weights", type=str, default=None, help="Path to model .pt")
    parser.add_argument("--conf", type=float, default=None)
    parser.add_argument("--iou", type=float, default=None)
    parser.add_argument("--imgsz", type=int, default=None)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Interface to bind to.")
    parser.add_argument("--port", type=int, default=8765)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))