import time
import math
import threading
import webbrowser
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pymavlink import mavutil

app = FastAPI(title="BlueROV2 Depth Telemetry API Gateway (FastAPI)")

# Enable CORS agar frontend bisa mengakses API tanpa terhalang kebijakan origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAVLINK_UDP_ENDPOINT = 'udpin:0.0.0.0:14551'  # Pasif/Listen dari BlueOS Client 127.0.0.1:14551
MAX_DEPTH_M = 2.0                             # Kedalaman maksimum default (meter)
HEARTBEAT_TIMEOUT_S = 10.0
RECV_TIMEOUT_S = 2.0
RECONNECT_DELAY_S = 3.0

# ---------------------------------------------------------------------------
# Shared state (di-protect dengan thread lock)
# ---------------------------------------------------------------------------
state_lock = threading.Lock()
current_source = 'dummy'  # 'dummy' atau 'real'

real_data = {
    'depth': 0.0,
    'rate': 0.0,
    'mavlink_connected': False,
}

dummy_data = {
    'depth': 0.0,
    'rate': 0.0,
}


# ---------------------------------------------------------------------------
# MAVLink background thread (Sama seperti logika Flask)
# ---------------------------------------------------------------------------
def mavlink_worker():
    while True:
        master = None
        try:
            print(f"[MAVLink] Connecting via {MAVLINK_UDP_ENDPOINT} ...")
            master = mavutil.mavlink_connection(MAVLINK_UDP_ENDPOINT)

            # Tunggu Heartbeat dari Pixhawk / BlueOS
            hb = master.wait_heartbeat(timeout=HEARTBEAT_TIMEOUT_S)
            if not hb:
                print("[MAVLink] No heartbeat received, retrying...")
                with state_lock:
                    real_data['mavlink_connected'] = False
                time.sleep(RECONNECT_DELAY_S)
                continue

            print(f"[MAVLink] Heartbeat received. System ID: {master.target_system}")
            with state_lock:
                real_data['mavlink_connected'] = True

            # Request stream data (POSITION untuk depth & EXTRA1 untuk VFR_HUD)
            master.mav.request_data_stream_send(
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_POSITION,  # Perbaikan namespace mavutil
                10, 1
            )
            master.mav.request_data_stream_send(
                master.target_system,
                master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_EXTRA1,    # Perbaikan namespace mavutil
                10, 1
            )

            # Main receive loop
            while True:
                msg = master.recv_match(
                    type=['GLOBAL_POSITION_INT', 'VFR_HUD'],
                    blocking=True,
                    timeout=RECV_TIMEOUT_S
                )
                if not msg:
                    print("[MAVLink] Timeout waiting for data, checking connection...")
                    with state_lock:
                        real_data['mavlink_connected'] = False
                    break  # Reconnect jika timeout

                with state_lock:
                    real_data['mavlink_connected'] = True

                msg_type = msg.get_type()
                if msg_type == 'GLOBAL_POSITION_INT':
                    # relative_alt dalam mm, bernilai negatif di bawah air -> konversi ke meter
                    depth_m = max(0.0, -(msg.relative_alt / 1000.0))
                    with state_lock:
                        real_data['depth'] = depth_m

                elif msg_type == 'VFR_HUD':
                    # climb: negatif = menyelam (diving), positif = muncul (surfacing)
                    rate_ms = -float(msg.climb)
                    with state_lock:
                        real_data['rate'] = rate_ms

        except Exception as e:
            print(f"[MAVLink] Error: {e}")
            with state_lock:
                real_data['mavlink_connected'] = False
            time.sleep(RECONNECT_DELAY_S)
        finally:
            try:
                if master is not None:
                    master.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Dummy data background thread (Simulasi osilasi sinuoid)
# ---------------------------------------------------------------------------
def dummy_worker():
    speed = 0.4
    t0 = time.time()
    while True:
        t = time.time() - t0
        depth = (MAX_DEPTH_M / 2.0) * (1 - math.cos(t * speed))
        rate = (MAX_DEPTH_M / 2.0) * math.sin(t * speed) * speed

        with state_lock:
            dummy_data['depth'] = depth
            dummy_data['rate'] = rate

        time.sleep(0.1)


# ---------------------------------------------------------------------------
# Pydantic Schema
# ---------------------------------------------------------------------------
class SourcePayload(BaseModel):
    source: str


# ---------------------------------------------------------------------------
# Startup Event
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    # 1. Jalankan background threads untuk MAVLink & Dummy Data
    threading.Thread(target=mavlink_worker, daemon=True).start()
    threading.Thread(target=dummy_worker, daemon=True).start()

    # 2. Buka browser otomatis saat server menyala
    print("[INFO] Meluncurkan browser ke halaman dashboard...")
    webbrowser.open("http://localhost:8007")


# ---------------------------------------------------------------------------
# Routes / Endpoints
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <body style='background:#111827; color:#ef4444; font-family:sans-serif; text-align:center; padding-top:100px;'>
            <h1>[ERROR] File 'index.html' Tidak Ditemukan!</h1>
            <p style='color:#9ca3af'>Pastikan file index.html diletakkan di folder yang SAMA dengan app.py</p>
        </body>
        """


@app.get("/api/telemetry")
async def get_telemetry():
    with state_lock:
        source = current_source
        if source == 'real':
            depth = real_data['depth']
            rate = real_data['rate']
            mavlink_connected = real_data['mavlink_connected']
        else:
            depth = dummy_data['depth']
            rate = dummy_data['rate']
            mavlink_connected = real_data['mavlink_connected']

    return {
        'source': source,
        'depth': round(depth, 4),
        'depth_cm': round(depth * 100.0, 2),
        'rate': round(rate, 4),
        'mavlink_connected': mavlink_connected,
        'max_depth_m': MAX_DEPTH_M,
        'max_depth_cm': MAX_DEPTH_M * 100.0,
    }


@app.post("/api/source")
async def set_source(payload: SourcePayload):
    global current_source
    if payload.source not in ('real', 'dummy'):
        raise HTTPException(status_code=400, detail='source must be "real" or "dummy"')

    with state_lock:
        current_source = payload.source

    return {'status': 'ok', 'source': current_source}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
