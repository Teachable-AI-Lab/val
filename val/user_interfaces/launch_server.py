from flask import Flask
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

@socketio.on('message')
def handle_message(data):
    """ Runs when a client sends a 'message' event """
    print(f'Received message: { data }')
    emit('message', data, broadcast=True)

@socketio.event
def on_log(message):
    try:
        with open('log.html', 'a') as log_file:
            log_file.write(message + '\n')
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    socketio.run(app, debug=True, host="localhost", port=4002)
