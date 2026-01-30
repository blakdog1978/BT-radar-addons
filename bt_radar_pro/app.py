import time
import json
import os
import threading
import logging
import requests
from flask import Flask, render_template_string, request, redirect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("RadarStates")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL = "http://supervisor/core/api/states"

# Memoria locale del Radar
trackers_found = {}
update_counter = 0

def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {"selected_tracker": None, "friendly_name": "", "selected_room": ""}

def save_settings(s):
    with open(CONFIG_FILE, 'w') as f: json.dump(s, f)

# --- MOTORE DI RIFLESSIONE STATI ---
def state_engine():
    global update_counter
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "content-type": "application/json",
    }
    
    while True:
        try:
            response = requests.get(HA_URL, headers=headers, timeout=5)
            if response.status_code == 200:
                states = response.json()
                update_counter += 1
                
                for s in states:
                    entity_id = s['entity_id']
                    # Filtriamo solo i tracker di Bermuda
                    if entity_id.startswith("device_tracker.bermuda_"):
                        attrs = s.get('attributes', {})
                        
                        # Estraiamo i dati utili
                        trackers_found[entity_id] = {
                            "name": attrs.get('friendly_name', entity_id),
                            "state": s.get('state', 'unknown'),
                            "scanner": attrs.get('scanner') or "In ricerca...",
                            "rssi": attrs.get('rssi', 'N/D'),
                            "distance": attrs.get('distance', 0)
                        }
            else:
                logger.error(f"Errore API HA: {response.status_code}")
        except Exception as e:
            logger.error(f"Errore Engine: {e}")
        
        time.sleep(2) # Aggiornamento ogni 2 secondi

threading.Thread(target=state_engine, daemon=True).start()

@app.route('/')
def index():
    settings = load_settings()
    rows = ""
    for eid, data in trackers_found.items():
        is_sel = eid == settings['selected_tracker']
        border = "border: 2px solid #58a6ff; background: #1c2128;" if is_sel else "border: 1px solid #333;"
        
        rows += f"""
        <div style="padding:15px; border-radius:12px; margin:10px 0; {border}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b>{data['name']}</b>
                <span style="color:#58a6ff; font-weight:bold;">{data['distance']} m</span>
            </div>
            <div style="font-size:0.8em; color:#8b949e; margin-top:5px;">
                Stato: {data['state']} | Scanner: <b>{data['scanner']}</b>
            </div>
            <form action="/select" method="post" style="margin-top:10px;">
                <input type="hidden" name="eid" value="{eid}">
                <button type="submit" style="width:100%; background:#238636; color:white; border:none; padding:8px; border-radius:6px; cursor:pointer;">
                    { 'TRACKER ATTIVO' if is_sel else 'SELEZIONA' }
                </button>
            </form>
        </div>
        """

    return f"""
    <html>
        <head><meta http-equiv="refresh" content="3">
        <style>body{{background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:20px; max-width:500px; margin:auto;}}
        .header{{background:#161b22; padding:15px; border-radius:12px; border:1px solid #30363d; margin-bottom:20px; text-align:center;}}
        </style></head>
        <body>
            <div class="header">
                <h2 style="margin:0; color:#58a6ff;">🛰️ Radar State Engine</h2>
                <small>Sincronizzato: {update_counter} volte</small>
            </div>
            {rows if trackers_found else "<p style='text-align:center;'>Nessun tracker Bermuda trovato negli stati...</p>"}
        </body>
    </html>
    """

@app.route('/select', methods=['POST'])
def select():
    s = load_settings()
    s["selected_tracker"] = request.form.get('eid')
    save_settings(s)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)