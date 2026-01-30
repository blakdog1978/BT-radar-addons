from flask import Flask, render_template_string, request, redirect, jsonify
import asyncio
import threading
import os
import json
from bleak import BleakScanner

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
discovered_devices = {}

# Caricamento impostazioni
def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {"selected_tracker": None, "friendly_name": "", "selected_room": ""}

# --- MOTORE DI SCANSIONE BLUETOOTH AUTONOMO ---
def scan_callback(device, advertisement_data):
    """Questa funzione viene chiamata ogni volta che viene rilevato un segnale BT"""
    mac = device.address
    rssi = advertisement_data.rssi
    name = advertisement_data.local_name or device.name or "Dispositivo Sconosciuto"
    
    # Calcolo distanza approssimativa (Pro Engine)
    # Formula: d = 10 ^ ((Measured Power - RSSI) / (10 * N))
    tx_power = -59 # Valore standard per iPhone/Android
    n = 2.0        # Fattore ambientale (2.0 = spazio aperto)
    distance = round(10**((tx_power - rssi) / (20)), 2)
    
    discovered_devices[mac] = {
        "name": name,
        "rssi": rssi,
        "dist": distance,
        "moving": "Si" if mac in discovered_devices and abs(discovered_devices[mac]['rssi'] - rssi) > 3 else "No"
    }

def start_ble_scanner():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    scanner = BleakScanner(scan_callback)
    loop.run_until_complete(scanner.start())
    loop.run_forever()

# Avviamo la scansione in un thread separato
threading.Thread(target=start_ble_scanner, daemon=True). obscurity = True

@app.route('/')
def index():
    settings = load_settings()
    # Ordiniamo i dispositivi per potenza di segnale (i più vicini in alto)
    sorted_devs = dict(sorted(discovered_devices.items(), key=lambda x: x[1]['rssi'], reverse=True))
    
    device_list_html = ""
    for mac, data in sorted_devs.items():
        is_sel = mac == settings['selected_tracker']
        border = "border: 2px solid #03a9f4;" if is_sel else "border: 1px solid #333;"
        device_list_html += f"""
        <div style="background: #1c1f26; margin: 10px 0; padding: 15px; border-radius: 12px; {border} display: flex; justify-content: space-between;">
            <div>
                <b style="color:{'#03a9f4' if is_sel else 'white'}">{data['name']}</b><br>
                <small style="color:#777;">MAC: {mac} | RSSI: {data['rssi']}</small>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 1.2em; font-weight: bold; color: #58a6ff;">{data['dist']} m</span><br>
                <form action="/set_tracker" method="post" style="margin:5px 0 0 0;">
                    <input type="hidden" name="tracker" value="{mac}">
                    <button type="submit" style="background:#238636; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer; font-size:10px;">SELEZIONA</button>
                </form>
            </div>
        </div>
        """

    return f"""
    <html>
        <head>
            <meta http-equiv="refresh" content="3"> <style>
                body {{ background: #0d1117; color: #c9d1d9; font-family: sans-serif; padding: 20px; }}
                .container {{ max-width: 500px; margin: auto; background: #161b22; padding: 20px; border-radius: 20px; border: 1px solid #30363d; }}
                h1 {{ color: #58a6ff; text-align: center; font-size: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛰️ Radar Engine Pro (Standalone)</h1>
                <p style="text-align:center; font-size: 0.8em; color: #777;">Motore di scansione attivo - No Bermuda</p>
                <div style="background: #21262d; padding: 10px; border-radius: 8px; margin-bottom: 20px; text-align:center;">
                    Tracker: <b style="color:#58a6ff">{settings['friendly_name'] or 'Nessuno'}</b> | Stanza: <b>{settings['selected_room'] or 'Nessuna'}</b>
                </div>
                {device_list_html if discovered_devices else "<p style='text-align:center;'>Scansione in corso...</p>"}
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
