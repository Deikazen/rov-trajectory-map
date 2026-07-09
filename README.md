# ROV Trajectory Map

Aplikasi dashboard sederhana untuk memantau lintasan ROV secara real-time dari data telemetri MAVLink/Pixhawk.

Frontend menampilkan peta top-down berbasis canvas, sementara backend FastAPI menyediakan data posisi melalui endpoint `/api/telemetry`.

## Fitur

- Menampilkan lintasan pergerakan ROV pada canvas
- Menandai posisi saat ini dengan indikator panah
- Menyimpan riwayat lintasan selama sesi berjalan
- Menyediakan tombol **Replay Path** dan **Clear**
- Menampilkan status koneksi backend (**ONLINE/OFFLINE**)
- Auto-open browser saat server dijalankan

## Struktur Proyek

- `main.py` — backend FastAPI + pembaca data MAVLink
- `index.html` — tampilan dashboard frontend
- `requirements.txt` — daftar dependency Python

## Kebutuhan

- Python 3.6+
- Access ke sumber telemetri MAVLink/Pixhawk
- Koneksi UDP ke `127.0.0.1:14551`

## Instalasi

```bash
pip install -r requirements.txt
```

Jika memakai virtual environment, aktifkan dulu environment yang sudah ada lalu jalankan perintah di atas.

## Menjalankan Aplikasi

```bash
python main.py
```

Server akan berjalan di:

- `http://localhost:8007`

Saat startup, aplikasi juga mencoba membuka browser otomatis ke halaman dashboard.

## Alur Kerja

1. Backend membaca telemetri MAVLink dari Pixhawk.
2. Data posisi disimpan ke state API.
3. Frontend melakukan polling ke `/api/telemetry` setiap 100 ms.
4. Canvas diperbarui untuk menggambar lintasan dan posisi terkini.

## Endpoint API

### `GET /`

Mengembalikan halaman dashboard `index.html`.

### `GET /api/telemetry`

Mengembalikan data telemetri dalam format JSON.

Contoh respons:

```json
{
  "roll": 0.0,
  "pitch": 0.0,
  "yaw": 0.0,
  "depth": 0.0,
  "x": 0.0,
  "y": 0.0
}
```

## Konfigurasi Penting

- Port backend: `8007`
- URL telemetry di frontend: `http://localhost:8007/api/telemetry`
- Port MAVLink input: `127.0.0.1:14551`
- Skala peta pada frontend: `12 x 12 meter`

## Catatan

- Jika data tidak muncul, pastikan Pixhawk/MAVLink sudah aktif dan mengirim data ke port yang benar.
- Jika browser tidak terbuka otomatis, buka manual `http://localhost:8007`.
- File `index.html` harus berada di folder yang sama dengan `main.py`.

