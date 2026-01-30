import time, json, os, threading, logging, requests
from flask import Flask, render_template_string, request, redirect
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("RadarPro")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL = "http://supervisor/core/api/states"

history = {}
trackers_found = {}

def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r') as f: return json.load(f)
    return default

def state_engine():
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}
    logger.info("🛡️ Motore Strict-Bluetooth Avviato...")
    
    while True:
        try:
            response = requests.get(HA_URL, headers=headers, timeout=5)
            if response.status_code == 200:
                new_data = {}
                for s in response.json():
                    eid = s['entity_id']
                    attrs = s.get('attributes', {})
                    
                    # FILTRO RIGIDO: Solo Bluetooth Low Energy e solo device_tracker
                    if eid.startswith("device_tracker.") and attrs.get('source_type') == "bluetooth_le":
                        
                        dist = attrs.get('distance', 0)
                        if dist is None: dist = 0
                        dist = float(dist)
                        
                        # Monitoriamo il movimento solo se la distanza è > 0
                        if dist > 0:
                            if eid not in history: history[eid] = deque(maxlen=5)
                            history[eid].append(dist)
                            motion = round(max(history[eid]) - min(history[eid]), 2)
                        else:
                            motion = 0

                        new_data[eid] = {
                            "name": attrs.get('friendly_name', eid).split("Bermuda")[0].strip(),
                            "scanner": attrs.get('scanner') or "Ricerca...",
                            "distance": round(dist, 2),
                            "motion": motion,
                            "active": dist > 0
                        }
                
                trackers_found.clear()
                trackers_found.update(new_data)
                
                # Log di diagnostica
                attivi = [d['name'] for d in trackers_found.values() if d['active']]
                if attivi:
                    logger.info(f"📡 Dispositivi BT in portata: {attivi}")
                
        except Exception as e:
            logger.error(f"❌ Errore API: {e}")
        time.sleep(2)

threading.Thread(target=state_engine, daemon=True).start()

@app.route('/')
def index():
    settings = load_json(CONFIG_FILE, {"selected_tracker": None})
    # Mostriamo solo i dispositivi con distanza > 0 (gli attivi)
    active_devs = {k: v for k, v in trackers_found.items() if v['active'] or k == settings['selected_tracker']}
    sorted_devs = sorted(active_devs.items(), key=lambda x: x[1]['name'])
    
    rows = ""
    for eid, data in sorted_devs:
        is_sel = eid == settings['selected_tracker']
        border = "border: 2px solid #58a6ff; background: #1c2128;" if is_sel else "border: 1px solid #333;"
        
        rows += f"""
        <div style="padding:10px; border-radius:8px; margin:5px 0; {border}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b>{"📱" if data['active'] else "💤"} {data['name']}</b>
                <b style="color:#58a6ff; font-size:1.2em;">{data['distance']}m</b>
            </div>
            <div style="font-size:0.7em; color:#8b949e; margin-top:4px;">
                Scanner: {data['scanner']} | Movimento: {data['motion']}m
            </div>
            <form action="/select" method="post" style="margin-top:8px;">
                <input type="hidden" name="eid" value="{eid}">
                <button type="submit" style="width:100%; background:#238636; color:white; border:none; padding:4px; border-radius:4px; cursor:pointer;">
                    { 'TRACKER SELEZIONATO' if is_sel else 'USA QUESTO' }
                </button>
            </form>
        </div> """

    return f"""
    <html>
        <head><meta http-equiv="refresh" content="3">
        <style>body{{background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:10px; max-width:400px; margin:auto;}}</style></head>
        <body>
            <h3 style="color:#58a6ff; text-align:center;">🛰️ Radar Strict v1.13</h3>
            {rows if rows else "<p style='text-align:center; color:#666;'>Nessun trasmettitore Bluetooth attivo rilevato...<br><br><small>Mettiti vicino a uno Shelly con il telefono!</small></p>"}
        </body>
    </html>
    """

@app.route('/select', methods=['POST'])
def select():
    eid = request.form.get('eid')
    with open(CONFIG_FILE, 'w') as f: json.dump({"selected_tracker": eid}, f)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)