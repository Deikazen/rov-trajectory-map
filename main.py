import asyncio
import math
import webbrowser  # <-- Library bawaan Python untuk buka browser
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  # <-- Untuk mengirimkan file HTML
from pymavlink import mavutil

app = FastAPI(title="ROV Telemetry API Gateway (Auto-Open Mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

telemetry_state = {
    "roll": 0.0, "pitch": 0.0, "yaw": 0.0,
    "depth": 0.0, "x": 0.0, "y": 0.0
}

try:
    pixhawk_link = mavutil.mavlink_connection('udpout:127.0.0.1:14551')
    print("[SUCCESS] Berhasil terhubung ke MAVLink via UDP.")
except Exception as e:
    print(f"[FATAL] Gagal inisialisasi koneksi MAVLink: {e}")
    pixhawk_link = None

async def read_pixhawk_telemetry_loop():
    if not pixhawk_link:
        return
    pixhawk_link.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
    pixhawk_link.mav.request_data_stream_send(pixhawk_link.target_system, pixhawk_link.target_component, MAV_DATA_STREAM_POSITION, 20, 1)
    pixhawk_link.mav.request_data_stream_send(pixhawk_link.target_system, pixhawk_link.target_component, MAV_DATA_STREAM_EXTRA1, 20, 1)

    print("[BACKGROUND TASK] Loop pembacaan MAVLink aktif...")
    while True:
        try:
            msg = pixhawk_link.recv_match(blocking=True, timeout=0.001)
            if msg:
                msg_type = msg.get_type()
                if msg_type == 'ATTITUDE':
                    telemetry_state["roll"] = round(math.degrees(msg.roll), 2)
                    telemetry_state["pitch"] = round(math.degrees(msg.pitch), 2)
                    telemetry_state["yaw"] = round((math.degrees(msg.yaw) + 360) % 360, 2)
                elif msg_type == 'VFR_HUD':
                    telemetry_state["depth"] = round(-msg.alt, 2)
                elif msg_type == 'LOCAL_POSITION_NED':
                    telemetry_state["x"] = round(msg.x, 2)
                    telemetry_state["y"] = round(msg.y, 2)
        except Exception as e:
            print(f"[WARNING] Gangguan pembacaan data: {e}")
        await asyncio.sleep(0.001)


@app.on_event("startup")
async def startup_event():
    # 1. Jalankan pembacaan data Pixhawk di background
    asyncio.ensure_future(read_pixhawk_telemetry_loop())
    
    # 2. OTOMATISASI: Perintahkan sistem operasi untuk langsung membuka browser
    print("[INFO] Meluncurkan browser ke halaman dashboard...")
    webbrowser.open("http://localhost:8007")


# --- ENDPOINT 1: Menampilkan Tampilan Utama (Frontend) ---
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """
    Endpoint root (/) untuk membaca file index.html dan mengirimkannya ke browser.
    """
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <body style='background:#111827; color:#ef4444; font-family:sans-serif; text-align:center; padding-top:100px;'>
            <h1>[ERROR] File 'index.html' Tidak Dikitukan!</h1>
            <p style='color:#9ca3af'>Pastikan file index.html diletakkan di folder yang SAMA dengan app.py</p>
        </body>
        """

# --- ENDPOINT 2: Menyediakan Data Telemetri ---
@app.get("/api/telemetry")
async def get_telemetry():
    return telemetry_state


if __name__ == "__main__":
    import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8007)