import cv2
import sys
import os
import json
import base64
import urllib.request
import numpy as np
import time
from datetime import datetime
from flask import Flask, jsonify
from threading import Lock
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# =====================================================
# Metadatos del servicio
# =====================================================
SERVICE_NAME = "servicio_capturador_imagen"
SERVICE_START_TIME = time.time()

# =====================================================
# Estado global
# =====================================================
state = {
    "config": None,
    "running": False,
    "last_snapshot_metadata": None,
    "last_error": None,
    "lock": Lock()
}

# =====================================================
# CARGA CONFIG
# =====================================================
def load_config():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    path = os.path.join(base, "config.json")
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================
# CAPTURAR FRAME DESDE MJPEG STREAM
# =====================================================
def get_frame_from_mjpeg(url: str):
    """Lee UNA imagen JPG desde un stream MJPEG."""
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            bytes_data = resp.read(250000)
    except Exception:
        return None

    # Buscar límites JPEG
    start = bytes_data.find(b'\xff\xd8')
    end = bytes_data.find(b'\xff\xd9')

    if start == -1 or end == -1:
        return None

    jpg = bytes_data[start:end + 2]

    # Decodificar
    img_np = np.frombuffer(jpg, dtype=np.uint8)
    frame = cv2.imdecode(img_np, cv2.IMREAD_COLOR)

    return frame


# =====================================================
# SNAPSHOT
# =====================================================
def capture_snapshot():
    url = state["config"].get("video_feed_url")

    frame = get_frame_from_mjpeg(url)
    if frame is None:
        return None, None

    # Resize
    canvas = state["config"].get("canvas_size", [512, 512])
    frame = cv2.resize(frame, tuple(canvas))

    # JPG
    q_table = {"low": 30, "medium": 60, "high": 90}
    quality = q_table.get(state["config"].get("quality", "medium"), 60)

    ret, buffer = cv2.imencode(
        ".jpg", frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    )

    if not ret:
        return None, None

    img_bytes = buffer.tobytes()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    metadata = {
        "datetimepic": datetime.utcnow().isoformat() + "Z",
        "resolution": f"{frame.shape[1]}x{frame.shape[0]}",
        "size_bytes": len(img_bytes),
        "format": "jpg"
    }

    return img_base64, metadata


# =====================================================
# ENDPOINT: SNAPSHOT
# =====================================================
@app.route("/snapshot", methods=["GET"])
def snapshot():
    img_base64, meta = capture_snapshot()

    if img_base64 is None:
        with state["lock"]:
            state["last_error"] = "Error capturando snapshot"

        return jsonify({"error": "No se pudo capturar imagen"}), 500

    with state["lock"]:
        state["last_snapshot_metadata"] = meta
        state["last_error"] = None

    return jsonify({
        "image": img_base64,
        "metadata": meta
    })


# =====================================================
# STATUS para GUI
# =====================================================
@app.route("/status", methods=["GET"])
@app.route("/api/v1/status", methods=["GET"])
def status():
    with state["lock"]:
        return jsonify({
            "servicio": SERVICE_NAME,
            "status": "ok" if state["last_error"] is None else "error",
            "running": state["running"],
            "uptime_sec": round(time.time() - SERVICE_START_TIME, 2),
            "last_snapshot_metadata": state["last_snapshot_metadata"],
            "last_error": state["last_error"],
            "timestamp": datetime.utcnow().isoformat()
        }), 200


# =====================================================
# GLOBAL ERROR HANDLER
# =====================================================
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({"error": e.description}), e.code

    with state["lock"]:
        state["last_error"] = str(e)

    return jsonify({"error": str(e)}), 500


# =====================================================
# RUN
# =====================================================
def run_service():
    state["config"] = load_config()
    state["running"] = True

    cfg = state["config"]
    host = cfg.get("host", "0.0.0.0")
    port = cfg.get("service_port", 5002)

    print(f"📸 {SERVICE_NAME} escuchando en {host}:{port}")
    app.run(host=host, port=port, threaded=True, debug=False)


if __name__ == "__main__":
    run_service()
