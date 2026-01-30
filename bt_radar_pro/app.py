from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def index():
    return """
    <html>
        <head><title>BT Radar Pro</title></head>
        <body style="background-color: #1c1c1c; color: white; font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1 style="color: #03a9f4;">🛰️ Radar Bluetooth Pro</h1>
            <p>L'Add-on è attivo correttamente!</p>
            <div style="border: 2px solid #333; padding: 20px; display: inline-block; border-radius: 10px;">
                <p>Pronto per la calibrazione...</p>
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    # Porta standard per Ingress di Home Assistant
    app.run(host='0.0.0.0', port=8099)
