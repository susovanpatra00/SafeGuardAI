"""
Client configuration.
Edit these values, or override via command-line args when running stream_client.py.
"""

# Server address. For remote/internet deployment, use your server's public IP
# or domain, e.g. "ws://203.0.113.5:8000/ws/stream" or "wss://myserver.com/ws/stream"
# (use wss:// instead of ws:// once the server is behind TLS/HTTPS).
SERVER_URL = "ws://127.0.0.1:8000/ws/stream"

# API key -- must match the server's PERIMETER_API_KEY env var (see server/auth.py).
# Sent as ?key=... on the websocket connection URL.
API_KEY = "CHANGE_ME_TO_MATCH_SERVER"

# Unique ID for this camera. Must be unique per client if you run multiple.
CAMERA_ID = "mac_webcam_01"

# Video source: 0 = default webcam, 1 = second camera, or a file path / RTSP URL.
SOURCE = 0

# Resize frames before sending, to save bandwidth. Set to None to keep original size.
RESIZE_WIDTH = 640
RESIZE_HEIGHT = 480

# JPEG compression quality (0-100). Lower = smaller/faster, higher = better quality.
JPEG_QUALITY = 70

# Target frames per second to send. Doesn't need to match camera's native FPS —
# sending fewer frames per second reduces bandwidth and server load.
SEND_FPS = 10

# How often to send a heartbeat message (seconds), so the server knows we're alive
# even during moments of network hiccup.
HEARTBEAT_INTERVAL_SEC = 10

# Reconnection behavior if the connection to the server drops.
RECONNECT_DELAY_SEC = 3
MAX_RECONNECT_DELAY_SEC = 30