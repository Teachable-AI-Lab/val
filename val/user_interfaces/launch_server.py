from flask import Flask
from flask import render_template
from flask_socketio import SocketIO
from flask_socketio import emit
from flask import send_from_directory

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(data):
    print(f'Received message: { data }')
    emit('message', data, broadcast=True, include_self=False)

@socketio.event
def on_log(message):
    try:
        with open('log.html', 'a') as log_file:
            log_file.write(message + '\n')
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    socketio.run(app, port=4000)
    print("I opened it")
