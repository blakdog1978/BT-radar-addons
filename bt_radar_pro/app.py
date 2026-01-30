from flask import Flask, render_template_string, request, redirect
import requests
import os
import json

app = Flask(__name__)

# Configurazione API e File
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')
HA_URL_STATES = "http://supervisor/core/api/states"
CONFIG_FILE = "/data/radar_settings.json"

def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"selected_tracker": None, "friendly_name": "", "selected_room": ""}

def save_settings(settings):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(settings, f)

def get_ha_data():
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}", "content-type": "application/json"}
    try:
        response = requests.get(HA_URL_STATES, headers=headers)
        return response.json()
    except:
        return []

def clean_name(name):
    # Rimuove underscore e mette le maiuscole correttamente
    return name.replace("_", " ").title()

@app.route('/')
def index():
    settings = load_settings()
    states = get_ha_data()
    
    # Discovery tracker da Bermuda
    trackers = [s for s in states if "bermuda" in s['entity_id'] and "distance" in s['entity_id']]
    
    # Estrazione aree/stanze pulite
    areas = []
    for s in states:
        area = s.get('attributes', {}).get('area_id')
        if area:
            clean_a = clean_name(area)
            if clean_a not in areas: areas.append(clean_a)
    
    if not areas:
        areas = ["Soggiorno", "Cucina", "Stanza Matrimoniale", "Bagno", "Ingresso"]

    tracker_list_html = ""
    for t in trackers:
        eid = t['entity_id'].split('.')[1].split('_distance')[0]
        is_sel = eid == settings['selected_tracker']
        border = "border: 2px solid #03a9f4; background: #232a35;" if is_sel else "border: 1px solid #333;"
        tracker_list_html += f"""
        <div style="background: #1c1f26; margin: 10px 0; padding: 15px; border-radius: 12px; {border} display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; flex-direction: column;">
                <span style="font-weight: bold; color: {'#03a9f4' if is_sel else 'white'};">{t['attributes'].get('friendly_name', eid)}</span>
                <span style="font-size: 0.8em; color: #777;">ID: {eid}</span>
            </div>
            <form action="/set_tracker" method="post" style="margin:0;">
                <input type="hidden" name="tracker" value="{eid}">
                <button type="submit" style="background: {'#03a9f4' if not is_sel else '#444'}; border: none; color: white; padding: 8px 16px; border-radius: 6px; cursor: pointer;">
                    { 'Selezionato' if is_sel else 'Usa questo' }
                </button>
            </form>
        </div>
        """

    room_options = "".join([f'<option value="{a}" {"selected" if a == settings["selected_room"] else ""}>{a}</option>' for a in sorted(areas)])

    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 20px; }}
                .app-card {{ max-width: 500px; margin: auto; background: #161b22; padding: 30px; border-radius: 20px; border: 1px solid #30363d; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }}
                h1 {{ color: #58a6ff; font-size: 24px; margin-bottom: 20px; text-align: center; }}
                input, select, button {{ width: 100%; padding: 12px; margin: 12px 0; border-radius: 10px; border: 1px solid #30363d; background: #0d1117; color: white; box-sizing: border-box; }}
                .save-btn {{ background: #238636; border: none; font-weight: bold; font-size: 16px; cursor: pointer; margin-top: 20px; }}
                .save-btn:hover {{ background: #2ea043; }}
                label {{ font-size: 13px; color: #8b949e; margin-left: 5px; }}
                .status-bar {{ background: #21262d; padding: 10px; border-radius: 8px; font-size: 0.9em; text-align: center; margin-bottom: 20px; border: 1px solid #30363d; }}
            </style>
        </head>
        <body>
            <div class="app-card">
                <h1>🛰️ Radar Control</h1>
                <div class="status-bar">
                    Tracker: <b style="color:#58a6ff">{settings['friendly_name'] if settings['friendly_name'] else 'Non impostato'}</b><br>
                    Stanza: <b style="color:#58a6ff">{settings['selected_room'] if settings['selected_room'] else 'Nessuna'}</b>
                </div>

                <h3>📱 Dispositivi in zona</h3>
                {tracker_list_html if trackers else "<p style='text-align:center; color:#777;'>Nessun tracker Bermuda rilevato...</p>"}

                <form action="/save_all" method="post" style="margin-top: 30px;">
                    <hr style="border:0; border-top: 1px solid #30363d; margin: 20px 0;">
                    <label>NOME PERSONALIZZATO</label>
                    <input type="text" name="friendly_name" value="{settings['friendly_name']}" placeholder="Es. iPhone di Gianni">
                    
                    <label>STANZA DA MONITORARE</label>
                    <select name="selected_room">
                        <option value="">-- Scegli Stanza --</option>
                        {room_options}
                    </select>
                    
                    <button type="submit" class="save-btn">SALVA IMPOSTAZIONI</button>
                </form>
            </div>
        </body>
    </html>
    """

@app.route('/set_tracker', methods=['POST'])
def set_tracker():
    settings = load_settings()
    settings["selected_tracker"] = request.form.get('tracker')
    save_settings(settings)
    return redirect('/')

@app.route('/save_all', methods=['POST'])
def save_all():
    settings = load_settings()
    settings["friendly_name"] = request.form.get('friendly_name')
    settings["selected_room"] = request.form.get('selected_room')
    save_settings(settings)
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)
