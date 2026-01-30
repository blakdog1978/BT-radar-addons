import asyncio
import json
import os
import threading
import logging
import websockets
from flask import Flask, render_template_string, request, redirect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("RadarWS")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
discovered_devices = {}

def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {"selected_tracker": None, "friendly_name": "", "selected_room": ""}

# --- MOTORE WEBSOCKET (Sincronizzato con HA) ---
async def listen_to_ha_bluetooth():
    uri = "ws://supervisor/core/api/websocket"
    async with websockets.connect(uri) as websocket:
        # 1. Autenticazione
        await websocket.send(json.dumps({
            "type": "auth",
            "access_token": SUPERVISOR_TOKEN
        }))
        
        # 2. Sottoscrizione agli eventi Bluetooth
        await websocket.send(json.dumps({
            "id": 1,
            "type": "bluetooth/subscribe",
        }))
        
        logger.info("✅ Collegato al flusso dati Bluetooth di Home Assistant!")
        
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "event":
                event = data.get("event", {})
                mac = event.get("address")
                rssi = event.get("rssi")
                source = event.get("source", "Interna") # Nome dello Shelly o Proxy
                
                if mac and rssi:
                    # Calcolo distanza
                    dist = round(10**((-59 - rssi) / 20), 2)
                    discovered_devices[mac] = {
                        "name": mac, # In WS riceviamo il MAC, il nome lo prenderemo dai settings
                        "rssi": rssi,
                        "dist": dist,
                        "proxy": source
                    }

def run_ws_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(listen_to_ha_bluetooth())

threading.Thread(target=run_ws_thread, daemon=True).start()

@app.route('/')
def index():
    settings = load_settings()
    # Ordiniamo per i più vicini
    sorted_devs = dict(sorted(discovered_devices.items(), key=lambda x: x[1]['rssi'], reverse=True))
    
    device_html = ""
    for mac, data in sorted_devs.items():
        is_sel = mac == settings['selected_tracker']
        border = "border: 2px solid #58a6ff;" if is_sel else "border: 1px solid #333;"
        device_html += f"""
        <div style="background:#1c1f26; padding:15px; border-radius:12px; margin:10px 0; {border}">
            <div style="display:flex; justify-content:space-between;">
                <b>{mac}</b>
                <span style="color:#58a6ff; font-weight:bold;">{data['dist']}m</span>
            </div>
            <div style="font-size:0.8em; color:#777;">Sentito da: {data['proxy']}</div>
            <form action="/set_tracker" method="post" style="margin-top:10px;">
                <input type="hidden" name="tracker" value="{mac}">
                <button type="submit" style="width:100%; background:#238636; color:white; border:none; padding:5px; border-radius:5px;">SELEZIONA</button>
            </form>
        </div>
        """

    return f"""
    <html>
        <head><meta http-equiv="refresh" content="3">
        <style>body{{background:#0d1117; color:white; font-family:sans-serif; padding:20px;}}</style></head>
        <body>
            <h1>🛰️ Radar Multi-Proxy</h1>
            <p>Stato: <b style="color:#58a6ff">In ascolto via WebSocket</b></p>
            <div style="background:#161b22; padding:20px; border-radius:15px; border:1px solid #30363d;">
                {device_html if discovered_devices else "In attesa di segnali BLE..."}
            </div>
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
