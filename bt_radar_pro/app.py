import asyncio
import json
import os
import threading
import logging
import websockets
from flask import Flask, render_template_string, request, redirect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("RadarDiagnostic")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')

discovered_devices = {}
total_events = 0
ws_status = "Inizializzazione..."
error_details = ""

async def monitor_bluetooth():
    global total_events, ws_status, error_details
    uri = "ws://supervisor/core/api/websocket"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                # 1. Handshake Iniziale
                msg = json.loads(await websocket.recv())
                
                # 2. Autenticazione
                await websocket.send(json.dumps({
                    "type": "auth",
                    "access_token": SUPERVISOR_TOKEN
                }))
                
                auth_resp = json.loads(await websocket.recv())
                if auth_resp.get("type") != "auth_ok":
                    ws_status = "❌ Autenticazione Fallita"
                    error_details = auth_resp.get("message", "Token non valido")
                    await asyncio.sleep(10)
                    continue

                # 3. Tentativo di Sottoscrizione
                # Usiamo un ID più alto per evitare conflitti
                await websocket.send(json.dumps({
                    "id": 100,
                    "type": "bluetooth/subscribe"
                }))
                
                sub_resp = json.loads(await websocket.recv())
                if sub_resp.get("success"):
                    ws_status = "✅ Collegato e in Ascolto"
                    error_details = ""
                    logger.info(ws_status)
                else:
                    ws_status = "⚠️ Sottoscrizione fallita"
                    # QUI CATTURIAMO IL MOTIVO REALE
                    error_info = sub_resp.get("error", {})
                    error_details = f"Codice: {error_info.get('code')} - Messaggio: {error_info.get('message')}"
                    logger.error(f"Errore HA: {error_details}")
                    await asyncio.sleep(10)
                    continue

                # 4. Loop Dati
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("type") == "event":
                        total_events += 1
                        event = data.get("event", {})
                        mac = event.get("address")
                        if mac:
                            rssi = event.get("rssi")
                            dist = round(10**((-60 - rssi) / 22), 2)
                            discovered_devices[mac] = {
                                "rssi": rssi,
                                "dist": dist,
                                "proxy": event.get("source", "Proxy")
                            }
        except Exception as e:
            ws_status = "❌ Errore Connessione"
            error_details = str(e)
            await asyncio.sleep(5)

threading.Thread(target=lambda: asyncio.run(monitor_bluetooth()), daemon=True).start()

@app.route('/')
def index():
    device_rows = "".join([f"<tr><td>{m}</td><td><b>{d['dist']}m</b></td><td>{d['proxy']}</td></tr>" for m, d in discovered_devices.items()])
    
    return f"""
    <html>
        <head><meta http-equiv="refresh" content="2">
        <style>
            body {{ background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:20px; }}
            .card {{ background:#161b22; border:1px solid #30363d; border-radius:12px; padding:20px; }}
            .error-box {{ background:#442a2a; border:1px solid #f85149; color:#ff7b72; padding:15px; border-radius:8px; margin:10px 0; font-size:0.9em; }}
            table {{ width:100%; margin-top:20px; border-collapse:collapse; }}
            th, td {{ padding:12px; border-bottom:1px solid #30363d; text-align:left; }}
        </style></head>
        <body>
            <div class="card">
                <h2>🛰️ Radar Diagnostic 1.7.3</h2>
                <p>Stato: <b>{ws_status}</b></p>
                
                { f'<div class="error-box"><b>Dettaglio Errore:</b><br>{error_details}</div>' if error_details else '' }
                
                <p>Eventi: <b>{total_events}</b></p>
                <table><tr><th>MAC</th><th>Dist</th><th>Proxy</th></tr>{device_rows}</table>
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)