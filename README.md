# ROV Trajectory Map

A simple dashboard application to monitor an ROV trajectory in real time using MAVLink/Pixhawk telemetry data.

The frontend renders a top-down canvas map, while the FastAPI backend serves telemetry data through the `/api/telemetry` endpoint.

## Features

- Display real-time ROV movement trajectory on a canvas
- Show current position with an arrow indicator
- Keep trajectory history during the active session
- Provide **Replay Path** and **Clear** controls
- Show backend connection status (**ONLINE/OFFLINE**)
- Automatically open the dashboard in a browser on startup

## Project Structure

- `main.py` — FastAPI backend + MAVLink telemetry reader
- `index.html` — frontend dashboard UI
- `requirements.txt` — Python dependencies

## Requirements

- Python 3.6+
- Access to a MAVLink/Pixhawk telemetry source
- UDP connection to `127.0.0.1:14551`

## Installation

```bash
pip install -r requirements.txt
```

If you use a virtual environment, activate it first, then run the command above.

## Running the Application

```bash
python main.py
```

The server runs at:

- `http://localhost:8007`

On startup, the app also attempts to open the dashboard in your browser automatically.

## Workflow

1. The backend reads MAVLink telemetry from Pixhawk.
2. Position and attitude data are stored in API state.
3. The frontend polls `/api/telemetry` every 100 ms.
4. The canvas is updated with the latest trajectory and current position.

## API Endpoints

### `GET /`

Returns the `index.html` dashboard page.

### `GET /api/telemetry`

Returns telemetry data in JSON format.

Example response:

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

## Important Configuration

- Backend port: `8007`
- Frontend telemetry URL: `http://localhost:8007/api/telemetry`
- MAVLink input address: `127.0.0.1:14551`
- Frontend map scale: `12 x 12 meters`

## Notes

- If telemetry data does not appear, ensure Pixhawk/MAVLink is active and sending data to the correct port.
- If the browser does not open automatically, open `http://localhost:8007` manually.
- `index.html` must be in the same directory as `main.py`.

## Source

- Repository: https://github.com/Deikazen/rov-trajectory-map

## References

- FastAPI documentation: https://fastapi.tiangolo.com/
- Uvicorn documentation: https://www.uvicorn.org/
- pymavlink (PyPI): https://pypi.org/project/pymavlink/
- MAVLink official documentation: https://mavlink.io/en/

## Author

- Deikazen
