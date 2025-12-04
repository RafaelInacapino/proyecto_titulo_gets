import time
import serial
import serial.tools.list_ports
from datetime import datetime
from threading import Lock, Thread
from flask import Flask, request, jsonify

app = Flask(__name__)

# =====================================================
# Tabla real de VID/PID de placas Arduino oficiales + clones
# =====================================================
ARDUINO_IDS = [
    # Arduino oficiales
    (0x2341, 0x0043),  # Uno
    (0x2341, 0x0001),  # Uno R1
    (0x2341, 0x0010),  # Mega 2560
    (0x2341, 0x8036),  # Leonardo
    (0x2341, 0x0243),  # Micro
    (0x2A03, 0x0043),  # Uno (AG)
    (0x2A03, 0x0010),  # Mega (AG)

    # Clones CH340 / CH341
    (0x1A86, 0x7523),

    # FTDI clones
    (0x0403, 0x6001),
]

# =====================================================
# Estado global
# =====================================================
state = {
    "arduino": None,
    "running": False,
    "last_command": None,
    "ultimo_estado_deseado": None,  # << solo ON/OFF
    "last_error": None,
    "lock": Lock(),
}

# =====================================================
# Buscar Arduino
# =====================================================
def buscar_arduino():
    puertos = serial.tools.list_ports.comports()

    for p in puertos:
        vid, pid = p.vid, p.pid

        if vid is None or pid is None:
            continue

        if (vid, pid) in ARDUINO_IDS:
            print(f"[OK] Arduino detectado → {p.device} ({p.description})")
            return p.device

    return None

# =====================================================
# Conectar
# =====================================================
def intentar_conectar():
    port = buscar_arduino()

    if not port:
        state["last_error"] = "Arduino no encontrado"
        return None

    try:
        ser = serial.Serial(port, 9600, timeout=1)
        time.sleep(2)  # reset Arduino
        print(f"[OK] Conectado a {port}")
        return ser
    except Exception as e:
        state["last_error"] = f"Error abriendo {port}: {e}"
        return None

# =====================================================
# Enviar comando real
# =====================================================
def enviar_comando(cmd: str):
    with state["lock"]:
        if state["arduino"] is None or not state["arduino"].is_open:
            return False

        try:
            state["arduino"].write((cmd + "\n").encode("ascii"))
            state["last_command"] = cmd
            print(f"[SEND] {cmd}")
            return True
        except Exception as e:
            print("[ERROR] Arduino desconectado durante envío")
            state["arduino"] = None
            state["last_error"] = str(e)
            return False

# =====================================================
# Enviar comando usuario
# =====================================================
def enviar_comando_usuario(cmd: str):
    cmd = cmd.strip().upper()

    # Solo ON/OFF se guardan como persistentes
    if cmd in ["ON", "OFF"]:
        state["ultimo_estado_deseado"] = cmd

    ok = enviar_comando(cmd)

    if not ok:
        print(f"[QUEUE] Arduino no conectado. Estado '{cmd}' queda en espera.")

    return ok

# =====================================================
# Reconexión infinita
# =====================================================
def loop_reconexion():
    while state["running"]:
        if state["arduino"] is None or not state["arduino"].is_open:
            print("[INFO] Buscando Arduino...")
            ser = intentar_conectar()

            if ser:
                with state["lock"]:
                    state["arduino"] = ser
                    state["last_error"] = None

                # Reenviar último ON/OFF
                if state["ultimo_estado_deseado"]:
                    time.sleep(1)
                    print(f"[SYNC] Reenviando: {state['ultimo_estado_deseado']}")
                    enviar_comando(state["ultimo_estado_deseado"])

        time.sleep(2)

# =====================================================
# API /alerta  (ON/OFF/cualquier comando)
# =====================================================
@app.route("/api/v1/alerta", methods=["POST"])
def alerta():
    body = request.get_json(force=True, silent=True) or {}
    accion = body.get("accion", body.get("action", "")).strip().upper()

    ok = enviar_comando_usuario(accion)

    return jsonify({
        "status": "ok" if ok else "pendiente",
        "accion_enviada": accion,
        "arduino_conectado": ok
    })

# =====================================================
# API STATUS  (NO BLOQUEA)
# =====================================================
@app.route("/api/v1/status")
@app.route("/status")
def status():
    with state["lock"]:
        conectado = state["arduino"] is not None and state["arduino"].is_open

    # Intento rápido de STATUS NO BLOQUEANTE
    try:
        enviar_comando("STATUS")   # NO se guarda como estado persistente
    except:
        pass

    with state["lock"]:
        return jsonify({
            "servicio": "servicio_alertador_incidente",
            "running": state["running"],
            "arduino_conectado": conectado,
            "ultimo_comando": state["last_command"],
            "ultimo_estado_deseado": state["ultimo_estado_deseado"],
            "ultimo_error": state["last_error"],
            "timestamp": datetime.utcnow().isoformat()
        })

# =====================================================
# RUN
# =====================================================
def run_service():
    state["running"] = True
    Thread(target=loop_reconexion, daemon=True).start()

    print("[INIT] Servicio iniciado.")
    print("[INIT] Buscando Arduino...")

    app.run(
        host="0.0.0.0",
        port=5007,
        debug=False,
        threaded=True
    )


if __name__ == "__main__":
    run_service()
