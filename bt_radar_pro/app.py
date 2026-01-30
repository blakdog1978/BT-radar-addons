import time
import json
import os
import threading
import requests
from flask import Flask, render_template_string, request, redirect
from collections import deque

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL = "http://supervisor/core/api/states"

history = {}
trackers_found = {}

# Parole chiave da ignorare (sensori di sistema e metadati)
BLACKLIST = [
    "count", "update", "ping", "online", "area", "floor", 
    "nearest", "connection", "state", "cappa", "power", "signal"
]

def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r') as f: return json.load(f)
    return default

def state_engine():
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}
    while True:
        try:
            response = requests.get(HA_URL, headers=headers, timeout=5)
            if response.status_code == 200:
                current_entities = response.json()
                new_data = {}
                
                for s in current_entities:
                    eid = s['entity_id']
                    
                    # FILTRO CHIRURGICO: Solo device_tracker che non sono nella blacklist
                    if eid.startswith("device_tracker.") and not any(word in eid for word in BLACKLIST):
                        attrs = s.get('attributes', {})
                        
                        # Consideriamo solo quelli che hanno una distanza o RSSI reale
                        dist = attrs.get('distance', 0)
                        if dist is None: dist = 0
                        
                        if eid not in history: history[eid] = deque(maxlen=10)
                        history[eid].append(dist)
                        
                        motion = 0
                        if len(history[eid]) > 2:
                            motion = max(history[eid]) - min(history[eid])

                        new_data[eid] = {
                            "name": attrs.get('friendly_name', eid).replace("Bermuda Tracker", "").strip(),
                            "scanner": attrs.get('scanner') or "In ricerca",
                            "distance": round(float(dist), 2),
                            "motion_score": round(motion, 2),
                            "is_moving": motion > 0.4
                        }
                
                # Sostituiamo i dati vecchi per evitare che la lista cresca all'infinito
                trackers_found.clear()
                trackers_found.update(new_data)
        except: pass
        time.sleep(1)

threading.Thread(target=state_engine, daemon=True).start()

@app.route('/')
def index():
    settings = load_json(CONFIG_FILE, {"selected_tracker": None})
    
    # Ordiniamo: per movimento e poi per distanza (i più vicini e attivi in alto)
    sorted_devs = sorted(trackers_found.items(), key=lambda x: (x[1]['is_moving'], -x[1]['distance'] if x[1]['distance'] > 0 else -99), reverse=True)
    
    # Limitiamo a 15 dispositivi per stabilizzare la UI
    display_devs = sorted_devs[:15]

    rows = ""
    for eid, data in display_devs:
        is_sel = eid == settings['selected_tracker']
        border = "border: 2px solid #58a6ff; background: #1c2128;" if is_sel else "border: 1px solid #333;"
        status_color = "#2ea043" if data['is_moving'] else "#8b949e"
        
        rows += f"""
        <div style="padding:12px; border-radius:10px; margin:8px 0; {border} height: 85px; overflow: hidden;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div style="width: 70%;">
                    <b style="font-size:1em; white-space: nowrap;">{data['name']}</b><br>
                    <small style="color:{status_color}; font-weight:bold;">
                        { "🏃 IN MOVIMENTO" if data['is_moving'] else "🏠 POSIZIONE FISSA" }
                    </small>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:1.2em; font-weight:bold; color:#58a6ff;">{data['distance']}m</span><br>
                    <small style="color:#666; font-size:0.7em;">{data['scanner']}</small>
                </div>
            </div>
            <form action="/select" method="post" style="margin-top:5px;">
                <input type="hidden" name="eid" value="{eid}">
                <button type="submit" style="width:100%; background:#238636; color:white; border:none; padding:4px; border-radius:4px; cursor:pointer; font-size:0.8em;">
                    { 'SELEZIONATO' if is_sel else 'USA PER RADAR' }
                </button>
            </form>
        </div> """

    return f"""
    <html>
        <head><meta http-equiv="refresh" content="2">
        <style>
            body {{ background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:10px; max-width:450px; margin:auto; overflow-x:hidden; }}
            .header {{ background:#161b22; padding:15px; border-radius:12px; border:1px solid #30363d; margin-bottom:15px; text-align:center; }}
        </style></head>
        <body>
            <div class="header">
                <h2 style="margin:0; color:#58a6ff; font-size:18px;">🛰️ Radar Pro: Selezione</h2>
                <p style="font-size:0.8em; color:#8b949e; margin:5px 0;">Visualizzati {len(display_devs)} dispositivi reali</p>
            </div>
            {rows if display_devs else "<p style='text-align:center;'>Filtraggio dispositivi in corso...</p>"}
        </body>
    </html>
    """

@app.route('/select', methods=['POST'])
def select():
    s = {"selected_tracker": request.form.get('eid')}
    with open(CONFIG_FILE, 'w') as f: json.dump(s, f)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)