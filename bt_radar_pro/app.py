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

# Dati dinamici
discovered_devices = {}
total_packets = 0 

def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {"selected_tracker": None, "friendly_name": "", "selected_room": ""}

async def listen_to_ha_bluetooth():
    global total_packets
    uri = "ws://supervisor/core/api/websocket"
    
    while True: # Loop di riconnessione automatica
        try:
            async with websockets.connect(uri) as websocket:
                # 1. Auth
                await websocket.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
                
                # 2. Subscribe a TUTTI gli eventi Bluetooth disponibili
                await websocket.send(json.dumps({
                    "id": 1,
                    "type": "bluetooth/subscribe",
                }))
                
                logger.info("✅ Connessione WebSocket stabilita!")
                
                async for message in websocket:
                    data = json.loads(message)
                    
                    # Debug: contiamo ogni messaggio che arriva da HA
                    total_packets += 1
                    
                    if data.get("type") == "event":
                        event = data.get("event", {})
                        mac = event.get("address")
                        rssi = event.get("rssi")
                        source = event.get("source", "Interna")
                        
                        if mac and rssi:
                            # Formula logaritmica per la distanza
                            # d = 10^((Measured Power - RSSI) / (10 * N))
                            dist = round(10**((-60 - rssi) / 20), 2)
                            
                            discovered_devices[mac] = {
                                "rssi": rssi,
                                "dist": dist,
                                "proxy": source.replace("_", " ").title()
                            }
        except Exception as e:
            logger.error(f"❌ Connessione persa: {e}. Riprovo tra 5 secondi...")
            await asyncio.sleep(5)

def run_ws_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(listen_to_ha_bluetooth())

threading.Thread(target=run_ws_thread, daemon=True).start()

@app.route('/')
def index():
    settings = load_settings()
    sorted_devs = dict(sorted(discovered_devices.items(), key=lambda x: x[1]['rssi'], reverse=True))
    
    device_html = ""
    for mac, data in sorted_devs.items():
        is_sel = mac == settings['selected_tracker']
        border = "border: 2px solid #58a6ff; background: #21262d;" if is_sel else "border: 1px solid #333;"
        device_html += f"""
        <div style="background:#1c1f26; padding:15px; border-radius:12px; margin:10px 0; {border}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="font-family:monospace;">{mac}</b>
                <span style="color:#58a6ff; font-size:1.2em; font-weight:bold;">{data['dist']}m</span>
            </div>
            <div style="font-size:0.8em; color:#777; margin-top:5px;">Proxy: {data['proxy']} | RSSI: {data['rssi']}</div>
            <form action="/set_tracker" method="post" style="margin-top:10px;">
                <input type="hidden" name="tracker" value="{mac}">
                <button type="submit" style="width:100%; background:#238636; color:white; border:none; padding:8px; border-radius:6px; cursor:pointer;">
                    { 'DISPOSITIVO ATTIVO' if is_sel else 'SELEZIONA QUESTO' }
                </button>
            </form>
        </div>
        """

    return f"""
    <html>
        <head>
            <meta http-equiv="refresh" content="2">
            <style>
                body{{background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:20px; max-width:500px; margin:auto;}}
                .header{{text-align:center; padding:20px; background:#161b22; border-radius:15px; border:1px solid #30363d; margin-bottom:20px;}}
                .packet-counter{{font-size:0.7em; color:#8b949e; margin-top:10px;}}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin:0; color:#58a6ff; font-size:22px;">🛰️ Radar Multi-Proxy</h1>
                <div class="packet-counter">Pacchetti ricevuti: {total_packets}</div>
            </div>
            
            <div style="margin-bottom:15px; font-size:0.9em;">
                Tracker: <b style="color:#58a6ff">{settings['friendly_name'] or 'Non impostato'}</b><br>
                Stanza: <b>{settings['selected_room'] or 'Non impostata'}</b>
            </div>

            {device_html if discovered_devices else "<p style='text-align:center; color:#777; padding:40px;'>In attesa di segnali...<br><small>Assicurati che il Bluetooth del telefono sia visibile.</small></p>"}
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
