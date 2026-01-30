import asyncio
import json
import os
import threading
import logging
import websockets
from flask import Flask, render_template_string, request, redirect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("RadarFix")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')

discovered_devices = {}
total_events = 0
ws_status = "Inizializzazione..."

async def monitor_bluetooth():
    global total_events, ws_status
    uri = "ws://supervisor/core/api/websocket"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                # 1. Aspettiamo il messaggio 'auth_required'
                welcome = json.loads(await websocket.recv())
                if welcome.get("type") != "auth_required":
                    ws_status = "❌ Protocollo non atteso"
                    continue

                # 2. Inviamo l'autenticazione
                await websocket.send(json.dumps({
                    "type": "auth",
                    "access_token": SUPERVISOR_TOKEN
                }))
                
                # 3. Verifichiamo se l'autenticazione è OK
                auth_resp = json.loads(await websocket.recv())
                if auth_resp.get("type") != "auth_ok":
                    ws_status = "❌ Token Rifiutato"
                    logger.error(f"{ws_status}: {auth_resp}")
                    await asyncio.sleep(10)
                    continue

                # 4. Sottoscrizione al Bluetooth
                await websocket.send(json.dumps({
                    "id": 1,
                    "type": "bluetooth/subscribe"
                }))
                
                sub_resp = json.loads(await websocket.recv())
                if sub_resp.get("success"):
                    ws_status = "✅ Collegato e in Ascolto"
                    logger.info(ws_status)
                else:
                    ws_status = "⚠️ Sottoscrizione fallita"
                    continue

                # 5. Loop di ricezione dati
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("type") == "event":
                        total_events += 1
                        event = data.get("event", {})
                        mac = event.get("address")
                        if mac:
                            rssi = event.get("rssi")
                            # Calcolo distanza (Path Loss Model)
                            dist = round(10**((-60 - rssi) / 22), 2)
                            discovered_devices[mac] = {
                                "rssi": rssi,
                                "dist": dist,
                                "proxy": event.get("source", "Proxy").replace("_", " ").title()
                            }
        except Exception as e:
            ws_status = f"❌ Errore: {str(e)}"
            logger.error(ws_status)
            await asyncio.sleep(5)

threading.Thread(target=lambda: asyncio.run(monitor_bluetooth()), daemon=True).start()

@app.route('/')
def index():
    # Carichiamo la lista ordinata per distanza
    sorted_devs = dict(sorted(discovered_devices.items(), key=lambda x: x[1]['rssi'], reverse=True))
    device_rows = "".join([f"<tr><td>{m}</td><td><b style='color:#58a6ff'>{d['dist']}m</b></td><td>{d['proxy']}</td></tr>" for m, d in sorted_devs.items()])
    
    return f"""
    <html>
        <head><meta http-equiv="refresh" content="2">
        <style>
            body {{ background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:20px; }}
            .card {{ background:#161b22; border:1px solid #30363d; border-radius:12px; padding:20px; }}
            .status-ok {{ color:#2ea043; font-weight:bold; }}
            .status-err {{ color:#f85149; font-weight:bold; }}
            table {{ width:100%; margin-top:20px; border-collapse:collapse; }}
            th, td {{ padding:12px; border-bottom:1px solid #30363d; text-align:left; }}
        </style></head>
        <body>
            <div class="card">
                <h2>🛰️ Radar Bluetooth Pro</h2>
                <p>Stato Sistema: <span class="{'status-ok' if '✅' in ws_status else 'status-err'}">{ws_status}</span></p>
                <p>Pacchetti ricevuti: <b>{total_events}</b></p>
                
                { "<table><tr><th>MAC Address</th><th>Distanza</th><th>Proxy</th></tr>" + device_rows + "</table>" if discovered_devices else "<p style='color:#8b949e;'>🔍 In attesa di pacchetti Bluetooth... prova a muovere il telefono.</p>" }
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)