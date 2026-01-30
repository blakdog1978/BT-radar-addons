import time, json, os, threading, logging, requests
from flask import Flask, jsonify, request, redirect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("RadarPro")

app = Flask(__name__)
CONFIG_FILE = "/data/radar_settings.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL = "http://supervisor/core/api/states"

trackers_found = {}

def state_engine():
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}
    logger.info("🕵️ Analisi profonda entità avviata...")
    
    while True:
        try:
            response = requests.get(HA_URL, headers=headers, timeout=5)
            if response.status_code == 200:
                new_data = {}
                entities = response.json()
                
                # Debug: Logghiamo i primi 2 tracker che troviamo per vedere i loro attributi
                debug_count = 0
                
                for s in entities:
                    eid = s['entity_id']
                    if eid.startswith("device_tracker."):
                        attrs = s.get('attributes', {})
                        
                        # Debug Log per le prime entità incontrate
                        if debug_count < 2:
                            logger.info(f"🔍 DEBUG Entity: {eid} | Attrs: {list(attrs.keys())} | Source: {attrs.get('source_type')}")
                            debug_count += 1
                        
                        # Filtro meno restrittivo per test
                        if "bermuda" in eid or attrs.get('source_type') == "bluetooth_le":
                            dist = attrs.get('distance', 0)
                            if dist is None: dist = 0
                            
                            new_data[eid] = {
                                "name": attrs.get('friendly_name', eid).split("Bermuda")[0].strip(),
                                "scanner": attrs.get('scanner') or "In ricerca",
                                "distance": round(float(dist), 2)
                            }
                
                trackers_found.clear()
                trackers_found.update(new_data)
        except Exception as e:
            logger.error(f"❌ Errore: {e}")
        time.sleep(2)

threading.Thread(target=state_engine, daemon=True).start()

@app.route('/api/data')
def get_data():
    return jsonify(trackers_found)

@app.route('/')
def index():
    return """
    <html>
        <head>
            <style>
                body { background:#0d1117; color:#c9d1d9; font-family:sans-serif; padding:15px; max-width:450px; margin:auto; }
                .card { background:#161b22; border:1px solid #30363d; border-radius:12px; padding:12px; margin:8px 0; }
                .btn { width:100%; background:#238636; color:white; border:none; padding:6px; border-radius:4px; cursor:pointer; margin-top:8px; }
            </style>
        </head>
        <body>
            <h3 style="color:#58a6ff; text-align:center;">🛰️ Radar Pro v1.14</h3>
            <div id="status" style="text-align:center; font-size:0.8em; color:#8b949e; margin-bottom:10px;">Aggiornamento dati...</div>
            <div id="device-list"></div>

            <script>
                async function updateData() {
                    try {
                        const response = await fetch('/api/data');
                        const data = await response.json();
                        const list = document.getElementById('device-list');
                        const status = document.getElementById('status');
                        
                        status.innerText = "Dati aggiornati alle " + new Date().toLocaleTimeString();
                        
                        let html = "";
                        for (const [eid, info] of Object.entries(data)) {
                            html += `
                            <div class="card">
                                <div style="display:flex; justify-content:space-between;">
                                    <b>📱 ${info.name}</b>
                                    <b style="color:#58a6ff;">${info.distance}m</b>
                                </div>
                                <div style="font-size:0.7em; color:#8b949e; margin-top:4px;">Scanner: ${info.scanner}</div>
                                <button class="btn" onclick="selectDevice('${eid}')">USA QUESTO</button>
                            </div>`;
                        }
                        if (html === "") html = "<p style='text-align:center; color:#666;'>In attesa di dispositivi Bluetooth...</p>";
                        list.innerHTML = html;
                    } catch (e) { console.error(e); }
                }
                
                function selectDevice(eid) {
                    fetch('/select', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: 'eid=' + encodeURIComponent(eid)
                    }).then(() => alert('Tracker impostato!'));
                }

                setInterval(updateData, 2000);
                updateData();
            </script>
        </body>
    </html>
    """

@app.route('/select', methods=['POST'])
def select():
    eid = request.form.get('eid')
    with open(CONFIG_FILE, 'w') as f: json.dump({"selected_tracker": eid}, f)
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)