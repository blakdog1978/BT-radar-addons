import asyncio
import json
import os
import threading
import logging
import websockets
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("RadarNative")

app = Flask(__name__)
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
raw_bt_data = {}

async def native_bluetooth_engine():
    uri = "ws://supervisor/core/api/websocket"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                # 1. Autenticazione
                await websocket.recv()
                await websocket.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
                auth_res = json.loads(await websocket.recv())
                
                if auth_res.get("type") != "auth_ok":
                    logger.error("❌ Token rifiutato")
                    await asyncio.sleep(10); continue

                # 2. Sottoscrizione al segnale BT nativo (Metodo Professionale)
                # Proviamo a chiedere i dati degli scanner (Shelly/ESP32)
                await websocket.send(json.dumps({
                    "id": 1,
                    "type": "bluetooth/subscribe"
                }))
                
                logger.info("📡 In attesa di dati Bluetooth nativi da HA...")
                
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("type") == "event":
                        event = data.get("event", {})
                        mac = event.get("address")
                        rssi = event.get("rssi")
                        if mac and rssi:
                            # Calcoliamo la distanza noi, come faceva Bermuda
                            # d = 10^((Measured Power - RSSI) / (10 * N))
                            dist = round(10**((-60 - rssi) / 22), 2)
                            raw_bt_data[mac] = {
                                "name": mac,
                                "distance": dist,
                                "proxy": event.get("source", "Interna"),
                                "rssi": rssi
                            }
                    elif data.get("id") == 1 and not data.get("success"):
                        logger.error(f"⚠️ HA ha negato l'accesso: {data.get('error', {}).get('message')}")

        except Exception as e:
            logger.error(f"🔄 Connessione persa: {e}")
            await asyncio.sleep(5)

threading.Thread(target=lambda: asyncio.run(native_bluetooth_engine()), daemon=True).start()

@app.route('/api/data')
def get_data():
    return jsonify(raw_bt_data)

@app.route('/')
def index():
    return """
    <html>
        <head>
            <style>
                body { background:#0d1117; color:white; font-family:sans-serif; padding:15px; }
                .card { background:#161b22; border:1px solid #333; padding:10px; margin:10px 0; border-radius:8px; }
            </style>
        </head>
        <body>
            <h2 style="text-align:center; color:#58a6ff;">🛰️ Radar Nativo (No Bermuda)</h2>
            <div id="status" style="text-align:center; color:#8b949e; font-size:0.8em;">Ricerca segnali...</div>
            <div id="list"></div>
            <script>
                async function update() {
                    const r = await fetch('/api/data');
                    const data = await r.json();
                    let html = "";
                    for(let mac in data) {
                        html += `<div class="card">
                            <b>${mac}</b> - <span style="color:#58a6ff">${data[mac].distance}m</span><br>
                            <small>Sentito da: ${data[mac].proxy} (RSSI: ${data[mac].rssi})</small>
                        </div>`;
                    }
                    document.getElementById('list').innerHTML = html || "<p style='text-align:center;'>Nessun dato Bluetooth nativo ricevuto.</p>";
                    document.getElementById('status').innerText = "Aggiornato: " + new Date().toLocaleTimeString();
                }
                setInterval(update, 2000);
            </script>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)