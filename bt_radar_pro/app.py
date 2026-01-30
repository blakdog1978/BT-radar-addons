from flask import Flask, render_template_string
import requests
import os

app = Flask(__name__)

# Recuperiamo il Token e l'URL dell'API di Home Assistant
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL = "http://supervisor/core/api/states"

def get_moving_devices():
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}", "content-type": "application/json"}
    try:
        response = requests.get(HA_URL, headers=headers)
        states = response.json()
        
        # Filtriamo solo i tracker o sensori legati a Bermuda/Bluetooth
        trackers = [s for s in states if "bermuda" in s['entity_id'] and "distance" in s['entity_id']]
        
        discovered = []
        for t in trackers:
            name = t.get('attributes', {}).get('friendly_name', t['entity_id'])
            dist = t.get('state', '0')
            # Logica semplice: se il dispositivo ha un attributo di 'distanza' valida, lo suggeriamo
            discovered.append({"id": t['entity_id'], "name": name, "dist": dist})
        return discovered
    except:
        return []

@app.route('/')
def index():
    devices = get_moving_devices()
    device_html = "".join([f"<li><b>{d['name']}</b> - Distanza attuale: {d['dist']}m</li>" for d in devices])
    
    return f"""
    <html>
        <head>
            <style>
                body {{ background: #101216; color: white; font-family: 'Segoe UI', sans-serif; padding: 30px; }}
                .card {{ background: #1c1f26; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
                .moving {{ color: #03a9f4; font-weight: bold; }}
                h1 {{ color: #03a9f4; border-bottom: 2px solid #333; padding-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🛰️ Radar Autodiscovery</h1>
                <p>Dispositivi BT rilevati in movimento:</p>
                <ul>{device_html if devices else "<li>Nessun dispositivo rilevato. Assicurati che Bermuda sia attivo.</li>"}</ul>
                <hr>
                <button onclick="location.reload()" style="background: #03a9f4; border: none; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                    Aggiorna Scansione
                </button>
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)
