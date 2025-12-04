import os
import sys
import json
import threading
import time
import cv2
from flask import Flask, Response, jsonify

app = Flask(__name__)

# ============================================================
# ESTADO GLOBAL
# ============================================================
def _ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")

state = {
    "service_name": "servicio_transmision_camara",
    "config": None,
    "cap": None,
    "running": False,
    "paused": False,
    "uptime_start": None,
    "frame": None,
    "last_error": None,
    "last_success": None,
    "lock": threading.Lock(),
    "current_cam_index": 0,
    "camera_list": [0, 1, 2, 3]
}


# ============================================================
# CONFIG
# ============================================================
def load_config():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    path = os.path.join(base, "config.json")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# GESTIÓN CÁMARAS ROBUSTA
# ============================================================
def try_open_camera(cam_id):
    try:
        cap = cv2.VideoCapture(cam_id)
        if not cap.isOpened():
            return None
        return cap
    except:
        return None


def rotate_to_next_camera():
    state["current_cam_index"] = (state["current_cam_index"] + 1) % len(state["camera_list"])
    return state["camera_list"][state["current_cam_index"]]


def recover_camera_infinite():
    """
    NO FALLA NUNCA.
    Intenta en bucle infinito encontrar alguna cámara disponible.
    """
    while True:
        cam_id = state["camera_list"][state["current_cam_index"]]
        cap = try_open_camera(cam_id)

        if cap:
            state["cap"] = cap
            state["last_error"] = None
            print(f"[RECOVER] Cámara detectada en ID {cam_id}")
            return

        # No hay cámara → rotar
        state["last_error"] = f"No hay cámara disponible (intentando ID {cam_id})"
        print(f"[WAIT] No se pudo abrir la cámara {cam_id}, rotando...")

        rotate_to_next_camera()
        time.sleep(1)   # evitar loops agresivos


# ============================================================
# LOOP CÁMARA
# ============================================================
def camera_loop():
    while state["running"]:
        cap = state["cap"]

        if cap is None:
            recover_camera_infinite()
            continue

        ret, frame = cap.read()

        if not ret:
            print("[ERROR] Frame inválido → recuperando cámara…")
            state["cap"] = None
            continue

        with state["lock"]:
            state["frame"] = frame.copy()
            state["last_success"] = _ts()

        time.sleep(0.03)


def start_camera():
    print("[INIT] Iniciando búsqueda de cámara...")
    state["cap"] = None
    state["running"] = True
    state["uptime_start"] = _ts()

    threading.Thread(target=camera_loop, daemon=True).start()


# ============================================================
# STREAMING
# ============================================================
def encode_frame(frame):
    _, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes()


def frame_generator():
    while True:
        with state["lock"]:
            frame = state["frame"].copy() if state["frame"] is not None else None

        if frame is None:
            time.sleep(0.1)
            continue

        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
               encode_frame(frame) +
               b"\r\n")


# ============================================================
# RUTAS
# ============================================================
@app.route("/video_feed")
def video_feed():
    return Response(frame_generator(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/v1/status")
def status_api():
    return jsonify({
        "service": state["service_name"],
        "running": state["running"],
        "paused": state["paused"],
        "uptime_start": state["uptime_start"],
        "last_error": state["last_error"],
        "last_success": state["last_success"],
        "has_frame": state["frame"] is not None,
        "current_camera": state["camera_list"][state["current_cam_index"]]
    })


# ============================================================
# RUN
# ============================================================
def run_service():
    state["config"] = load_config()

    start_camera()  # JAMÁS FALLA

    cfg = state["config"]
    host = cfg.get("host", "0.0.0.0")
    port = cfg.get("stream_port", 5000)

    print(f"[READY] Servicio iniciado en http://{host}:{port}")

    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    run_service()
