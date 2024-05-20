from flask import Flask
from flask import render_template
from flask_socketio import SocketIO
from flask_socketio import emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('chat.html')

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


if __name__ == '__main__':
    socketio.run(app, port=4000)
