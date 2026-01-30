import time
import json
import os
import threading
import logging
import requests
from flask import Flask, render_template_string, request, redirect
from collections import deque

# Configurazione Log Professionale
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RadarPro")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL = "http://supervisor/core/api/states"

history = {}
trackers_found = {}
BLACKLIST = ["count", "update", "ping", "online", "area", "floor", "nearest", "connection", "state", "cappa", "power", "signal"]

def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r') as f: return json.load(f)
    return default

def state_engine():
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}
    logger.info("🚀 Motore di scansione avviato. Analizzo le entità di Home Assistant...")
    
    last_log_time = 0
    
    while True:
        try:
            response = requests.get(HA_URL, headers=headers, timeout=5)
            if response.status_code == 200:
                current_entities = response.json()
                new_data = {}
                
                for s in current_entities:
                    eid = s['entity_id']
                    if eid.startswith("device_tracker."):
                        # Controllo Blacklist
                        if any(word in eid for word in BLACKLIST):
                            continue
                            
                        attrs = s.get('attributes', {})
                        dist = attrs.get('distance', 0)
                        if dist is None: dist = 0
                        
                        if eid not in history: history[eid] = deque(maxlen=10)
                        history[eid].append(float(dist))
                        
                        motion = max(history[eid]) - min(history[eid]) if len(history[eid]) > 2 else 0
                        is_moving = motion > 0.4

                        new_data[eid] = {
                            "name": attrs.get('friendly_name', eid).replace("Bermuda Tracker", "").strip(),
                            "scanner": attrs.get('scanner') or "In ricerca",
                            "distance": round(float(dist), 2),
                            "motion": round(motion, 2),
                            "is_moving": is_moving
                        }

                trackers_found.clear()
                trackers_found.update(new_data)

                # LOGGING PERIODICO (Ogni 10 secondi mostra un riassunto nei log)
                if time.time() - last_log_time > 10:
                    moving = [d['name'] for d in trackers_found.values() if d['is_moving']]
                    logger.info(f"📊 Radar Status: {len(trackers_found)} disp. filtrati | In movimento: {moving if moving else 'Nessuno'}")
                    last_log_time = time.time()

        except Exception as e:
            logger.error(f"❌ Errore nel recupero stati: {e}")
        
        time.sleep(2)

threading.Thread(target=state_engine, daemon=True).start()

@app.route('/')
def index():
    settings = load_json(CONFIG_FILE, {"selected_tracker": None})
    # Ordine stabile: Alfabetico per nome (così la lista non salta più se cambiano le distanze)
    sorted_devs = sorted(trackers_found.items(), key=lambda x: x[1]['name'])
    
    rows = ""
    for eid, data in sorted_devs:
        is_sel = eid == settings['selected_tracker']
        border = "border: 2px solid #58a6ff; background: #1c2128;" if is_sel else "border: 1px solid #333;"
        m_icon = "🏃" if data['is_moving'] else "🏠"
        
        rows += f"""
        <div style="padding:10px; border-radius:8px; margin:5px 0; {border} font-size: 0.9em;">
            <div style="display:flex; justify-content:space-between;">
                <b>{m_icon} {data['name']}</b>
                <b style="color:#58a6ff;">{data['distance']}m</b>
            </div>
            <div style="font-size:0.75em; color:#8b949e; margin:4px 0;">
                Sorgente: {data['scanner']} | Movimento: {data['motion']}m
            </div>
            <form action="/select" method="post" style="margin:0;">
                <input type="hidden" name="eid" value="{eid}">
                <input type="hidden" name="name" value="{data['name']}">
                <button type="submit" style="width:100%; background:#238636; color:white; border:none; padding:3px; border-radius:4px; cursor:pointer; font-size:0.8em;">
                    { 'TRACKER ATTIVO' if is_sel else 'SELEZIONA' }
                </button>
            </form>
        </div> """

    return f"""
    <html>
        <head><meta http-equiv="refresh" content="5"> <style>body{{background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:10px; max-width:400px; margin:auto;}}</style></head>
        <body>
            <h3 style="color:#58a6ff; text-align:center;">🛰️ Radar Pro v1.12</h3>
            <p style="font-size:0.7em; text-align:center; color:#8b949e;">Controlla i log dell'Add-on per il debug avanzato</p>
            {rows if trackers_found else "<p>In scansione...</p>"}
        </body>
    </html>
    """

@app.route('/select', methods=['POST'])
def select():
    eid = request.form.get('eid')
    name = request.form.get('name')
    logger.info(f"🎯 TARGET SELEZIONATO: {name} ({eid})")
    with open(CONFIG_FILE, 'w') as f: 
        json.dump({"selected_tracker": eid}, f)
    return redirect('/')

if __name__ == '__main__':
    logger.info("🌐 Interfaccia Web pronta sulla porta 8099")
    app.run(host='0.0.0.0', port=8099)