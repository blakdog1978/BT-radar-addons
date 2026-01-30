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

# Memoria storica per rilevare il movimento (max 10 campioni per device)
history = {}
trackers_found = {}

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
                for s in response.json():
                    # Monitoriamo TUTTI i device tracker e sensori bluetooth/bermuda
                    eid = s['entity_id']
                    if any(x in eid for x in ["bermuda", "bluetooth", "device_tracker"]):
                        attrs = s.get('attributes', {})
                        dist = attrs.get('distance', 0)
                        
                        # Aggiorna storico per calcolo movimento
                        if eid not in history: history[eid] = deque(maxlen=10)
                        history[eid].append(dist)
                        
                        # Calcolo varianza (Motion Score)
                        motion = 0
                        if len(history[eid]) > 2:
                            motion = max(history[eid]) - min(history[eid])

                        trackers_found[eid] = {
                            "name": attrs.get('friendly_name', eid),
                            "scanner": attrs.get('scanner') or "Statico",
                            "distance": dist,
                            "motion_score": round(motion, 2),
                            "is_moving": motion > 0.5
                        }
        except: pass
        time.sleep(1)

threading.Thread(target=state_engine, daemon=True).start()

@app.route('/')
def index():
    settings = load_json(CONFIG_FILE, {"selected_tracker": None, "selected_room": "Nessuna"})
    
    # Ordiniamo: Prima quelli che si muovono, poi gli altri
    sorted_devs = sorted(trackers_found.items(), key=lambda x: x[1]['is_moving'], reverse=True)

    rows = ""
    for eid, data in sorted_devs:
        is_sel = eid == settings['selected_tracker']
        motion_label = "🏃 IN MOVIMENTO" if data['is_moving'] else "🏠 STATICO"
        color = "#2ea043" if data['is_moving'] else "#8b949e"
        border = "border: 2px solid #58a6ff; background: #1c2128;" if is_sel else "border: 1px solid #333;"
        
        rows += f"""
        <div style="padding:15px; border-radius:12px; margin:10px 0; {border}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="max-width: 70%;">
                    <b style="font-size:1.1em;">{data['name']}</b><br>
                    <span style="color:{color}; font-size:0.8em; font-weight:bold;">{motion_label} (Δ {data['motion_score']}m)</span>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:1.4em; font-weight:bold; color:#58a6ff;">{data['distance']}m</span><br>
                    <small style="color:#666;">{data['scanner']}</small>
                </div>
            </div>
            <form action="/select" method="post" style="margin-top:10px;">
                <input type="hidden" name="eid" value="{eid}">
                <button type="submit" style="width:100%; background:#238636; color:white; border:none; padding:8px; border-radius:6px; cursor:pointer; font-weight:bold;">
                    { 'SORGENTE ATTIVA' if is_sel else 'USA PER CALIBRAZIONE' }
                </button>
            </form>
        </div> """

    return f"""
    <html>
        <head><meta http-equiv="refresh" content="2">
        <style>
            body {{ background:#0d1117; color:#c9d1d9; font-family:-apple-system, sans-serif; padding:15px; max-width:600px; margin:auto; }}
            .header {{ background: linear-gradient(145deg, #1c2128, #161b22); padding:20px; border-radius:15px; border:1px solid #30363d; margin-bottom:20px; text-align:center; }}
        </style></head>
        <body>
            <div class="header">
                <h1 style="margin:0; color:#58a6ff;">🛰️ Radar Smart Discovery</h1>
                <p style="font-size:0.9em; color:#8b949e;">Analisi in tempo reale di {len(trackers_found)} dispositivi</p>
            </div>
            <div style="margin-bottom:20px; padding:10px; background:#442a2a; border-radius:10px; border:1px solid #f85149; font-size:0.85em; display: {'block' if not settings['selected_tracker'] else 'none'};">
                ⚠️ <b>Consiglio:</b> Seleziona un dispositivo marcato come <b>IN MOVIMENTO</b> per una calibrazione precisa.
            </div>
            {rows if trackers_found else "<p style='text-align:center; padding:50px;'>Ricerca segnali nell'aria...</p>"}
        </body>
    </html>
    """

@app.route('/select', methods=['POST'])
def select():
    s = load_json(CONFIG_FILE, {"selected_tracker": None})
    s["selected_tracker"] = request.form.get('eid')
    with open(CONFIG_FILE, 'w') as f: json.dump(s, f)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)