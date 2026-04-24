from datetime import datetime, timezone
import json
import os

from flask import Flask
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")
LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'log.html'))


def append_user_log(event):
    """Append user interaction logs as JSON lines."""
    payload = event if isinstance(event, dict) else {"message": str(event)}
    payload.setdefault("server_timestamp", datetime.now(timezone.utc).isoformat())
    payload.setdefault("source", "val_web_gui")

    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as log_file:
            log_file.write(json.dumps(payload, ensure_ascii=False) + '\n')
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@socketio.on('message')
def handle_message(data):
    """ Runs when a client sends a 'message' event """
    emit('message', data, broadcast=True)

@socketio.on('on_log')
@socketio.on('on log')
def on_log(message):
    return append_user_log(message)

if __name__ == '__main__':
    socketio.run(app, debug=True, host="localhost", port=4002)
