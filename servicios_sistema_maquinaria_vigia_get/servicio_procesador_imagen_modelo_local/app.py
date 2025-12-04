import os
import sys
import json
import base64
import tempfile
import cv2
import numpy as np
from datetime import datetime
import time
from flask import Flask, request, jsonify
from inference_sdk import InferenceHTTPClient
from threading import Lock
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# =====================================================
# Metadatos del servicio
# =====================================================
SERVICE_NAME = "servicio_procesador_imagen_modelo_nube"
SERVICE_START_TIME = time.time()

# =====================================================
# Estado global
# =====================================================
state = {
    "config": None,
    "client": None,
    "running": False,
    "last_result": None,
    "last_error": None,
    "lock": Lock()
}

# =====================================================
# CONFIG
# =====================================================
def load_config():
    base_path = os.path.dirname(
        sys.executable if getattr(sys, 'frozen', False)
        else os.path.abspath(__file__)
    )

    config_path = os.path.join(base_path, "config.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"No se encontró config.json en {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_client():
    cfg = state["config"]
    state["client"] = InferenceHTTPClient(
        api_url=cfg["api_url"],
        api_key=cfg["roboflow_api_key"]
    )


# =====================================================
# UTILIDADES
# =====================================================
def base64_to_image(b64_string):
    try:
        data = base64.b64decode(b64_string)
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        return img
    except:
        return None


def image_to_base64(img):
    ok, buffer = cv2.imencode(".jpg", img)
    if not ok:
        raise RuntimeError("Error codificando imagen anotada")

    return base64.b64encode(buffer).decode("utf-8")


def extract_predictions(raw):
    if isinstance(raw, list) and len(raw) > 0:
        raw = raw[0]

    if not isinstance(raw, dict):
        return []

    preds_root = raw.get("predictions")
    if not isinstance(preds_root, dict):
        return []

    preds_list = preds_root.get("predictions")
    return preds_list if isinstance(preds_list, list) else []


def draw_predictions(img, predictions):
    for pred in predictions:
        try:
            x = int(pred["x"])
            y = int(pred["y"])
            w = int(pred["width"])
            h = int(pred["height"])
        except:
            continue

        class_name = pred.get("class", "obj")
        conf = pred.get("confidence", 0.0)

        x1 = max(0, x - w // 2)
        y1 = max(0, y - h // 2)
        x2 = x + w // 2
        y2 = y + h // 2

        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.putText(
            img,
            f"{class_name} {conf:.2f}",
            (x1, max(10, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (0, 255, 0), 2
        )

    return img


# =====================================================
# ENDPOINT PRINCIPAL
# =====================================================
@app.route("/procesar", methods=["POST"])
def procesar():
    data = request.get_json()
    if not data or "image" not in data:
        return jsonify({"error": "Falta campo 'image'"}), 400

    tmp_path = None

    try:
        img = base64_to_image(data["image"])
        if img is None:
            return jsonify({"error": "Imagen base64 inválida"}), 400

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        cv2.imwrite(tmp.name, img)
        tmp_path = tmp.name

        cfg = state["config"]

        raw_result = state["client"].run_workflow(
            workspace_name=cfg["workspace_name"],
            workflow_id=cfg["workflow_id"],
            images={"image": tmp_path},
            use_cache=False
        )

        predictions = extract_predictions(raw_result)
        annotated = draw_predictions(img.copy(), predictions)
        annotated_b64 = image_to_base64(annotated)

        result = {
            "predicciones": predictions,
            "count": len(predictions),
            "imagen": annotated_b64,
            "raw": raw_result
        }

        with state["lock"]:
            state["last_result"] = result
            state["last_error"] = None

        return jsonify(result), 200

    except Exception as e:
        with state["lock"]:
            state["last_error"] = str(e)
        return jsonify({"error": str(e)}), 500

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass


# =====================================================
# STATUS para GUI
# =====================================================
@app.route("/status", methods=["GET"])
@app.route("/api/v1/status", methods=["GET"])
def status():
    with state["lock"]:
        return jsonify({
            "servicio": SERVICE_NAME,
            "running": state["running"],
            "status": "ok" if state["last_error"] is None else "error",
            "last_result": state["last_result"],
            "last_error": state["last_error"],
            "uptime_sec": round(time.time() - SERVICE_START_TIME, 2),
            "timestamp": datetime.utcnow().isoformat()
        })


# =====================================================
# GLOBAL ERROR HANDLER
# =====================================================
@app.errorhandler(Exception)
def handle_exception(e):
    if hasattr(e, "code"):
        return jsonify({"error": str(e)}), e.code

    with state["lock"]:
        state["last_error"] = str(e)

    return jsonify({"error": str(e)}), 500


# =====================================================
# RUN
# =====================================================
def run_service():
    state["config"] = load_config()
    init_client()
    state["running"] = True

    cfg = state["config"]
    host = cfg.get("host", "0.0.0.0")
    port = cfg.get("service_port", 5003)

    print(f"🤖 {SERVICE_NAME} escuchando en {host}:{port}")
    app.run(host=host, port=port, threaded=True, debug=False)


if __name__ == "__main__":
    run_service()
