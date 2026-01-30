import asyncio
import json
import os
import threading
import logging
import websockets
from flask import Flask, render_template_string, request, redirect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("RadarBermuda")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')

# Dati Radar
discovered_devices = {}
proxies_found = set()
total_events = 0

def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {"selected_tracker": None, "friendly_name": "", "selected_room": ""}

async def bermuda_engine():
    global total_events
    uri = "ws://supervisor/core/api/websocket"
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                # Auth
                await websocket.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
                auth_res = await websocket.recv()
                
                # Sottoscrizione a TUTTI i dati Bluetooth (come fa il coordinator)
                await websocket.send(json.dumps({
                    "id": 1,
                    "type": "bluetooth/subscribe",
                }))
                
                logger.info("🚀 Motore Bermuda-Style avviato. In ascolto dei proxy...")
                
                async for message in websocket:
                    data = json.loads(message)
                    if data.get("type") == "event":
                        total_events += 1
                        event = data.get("event", {})
                        mac = event.get("address")
                        rssi = event.get("rssi")
                        source = event.get("source", "Server Locale")
                        
                        if mac and rssi:
                            proxies_found.add(source)
                            # Formula Bermuda: Distanza basata su RSSI e attenuazione ambiente
                            # Usiamo -60 come reference power a 1 metro
                            dist = round(10**((-60 - rssi) / (10 * 2.2)), 2)
                            
                            # Aggiorniamo il database in tempo reale
                            discovered_devices[mac] = {
                                "rssi": rssi,
                                "dist": dist,
                                "proxy": source.replace("_", " ").title(),
                                "last_seen": total_events
                            }
        except Exception as e:
            logger.error(f"❌ Errore connessione: {e}")
            await asyncio.sleep(5)

# Avvio del motore in background
threading.Thread(target=lambda: asyncio.run(bermuda_engine()), daemon=True).start()

@app.route('/')
def index():
    settings = load_settings()
    # Ordina: i più vicini in alto
    sorted_devs = dict(sorted(discovered_devices.items(), key=lambda x: x[1]['rssi'], reverse=True))
    
    device_html = ""
    for mac, data in sorted_devs.items():
        is_sel = mac == settings['selected_tracker']
        style = "border: 2px solid #58a6ff; background: #1c2128;" if is_sel else "border: 1px solid #30363d;"
        
        device_html += f"""
        <div style="padding:15px; border-radius:12px; margin:10px 0; {style}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-family:monospace; font-weight:bold;">{mac}</span>
                <span style="color:#58a6ff; font-size:1.3em;">{data['dist']}m</span>
            </div>
            <div style="font-size:0.8em; color:#8b949e; margin-top:5px;">
                📡 Sentito da: <b>{data['proxy']}</b> | RSSI: {data['rssi']}
            </div>
            <form action="/set_tracker" method="post" style="margin-top:10px;">
                <input type="hidden" name="tracker" value="{mac}">
                <button type="submit" style="width:100%; background:#238636; color:white; border:none; padding:8px; border-radius:6px; cursor:pointer;">
                    { 'TRACKER ATTIVO' if is_sel else 'IMPOSTA COME TRACKER' }
                </button>
            </form>
        </div>
        """

    return f"""
    <html>
        <head>
            <meta http-equiv="refresh" content="2">
            <style>
                body {{ background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:20px; max-width:550px; margin:auto; }}
                .status-box {{ background:#161b22; border:1px solid #30363d; border-radius:15px; padding:20px; margin-bottom:20px; }}
                .badge {{ background:#21262d; padding:4px 10px; border-radius:10px; font-size:0.8em; border:1px solid #444; }}
            </style>
        </head>
        <body>
            <div class="status-box">
                <h2 style="margin:0; color:#58a6ff;">🛰️ Radar Bermuda-Mode</h2>
                <div style="margin-top:10px; font-size:0.9em;">
                    Proxy attivi: <span style="color:#2ea043;">{len(proxies_found)}</span> | 
                    Segnali ricevuti: <span style="color:#2ea043;">{total_events}</span>
                </div>
                <div style="margin-top:10px; font-size:0.8em; color:#8b949e;">
                    Target: <b>{settings['friendly_name'] or 'Non impostato'}</b> in <b>{settings['selected_room'] or 'Nessuna'}</b>
                </div>
            </div>

            {device_html if discovered_devices else "<p style='text-align:center; padding:40px; color:#8b949e;'>🔍 Ricerca segnali Bluetooth dai proxy Shelly...</p>"}
        </body>
    </html>
    """

@app.route('/set_tracker', methods=['POST'])
def set_tracker():
    s = load_settings()
    s["selected_tracker"] = request.form.get('tracker')
    with open(CONFIG_FILE, 'w') as f: json.dump(s, f)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)