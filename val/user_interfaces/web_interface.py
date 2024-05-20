from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading

class WebInterface:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'secret!'
        self.socketio = SocketIO(self.app)
        self.user_task = None
        self.subtasks = None
        self.response_event = threading.Event()
        self.response = None

        @self.app.route('/')
        def index():
            return render_template('chat.html')

        @self.socketio.on('connect')
        def handle_connect():
            print('Client connected')
            self.request_user_task()

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('Client disconnected')

        @self.socketio.on('response')
        def handle_response(data):
            print('Received message:', data)
            self.response = data['response']
            self.response_event.set()
            
        @self.socketio.on('map_confirmation_response')
        def on_confirm(data):
            print(f"map_confirmation_response:{data}" )
        
        self.run()

    def run(self):
        threading.Thread(target=self.socketio.run, args=(self.app,)).start()

    def request_user_task(self) -> str:
        self.socketio.emit('request_user_task', {'text': 'How can I help you today?'})
        print("The message is emitted")
        self.response_event.wait()
        return self.response
    
    def ask_subtasks(self, user_task: str) -> str:
        self.socketio.emit('message', {'text': f"What are the steps for completing the task '{user_task}'?"})
        self.response_event.wait()  # Wait for the response
        return self.response

    def map_confirmation(self, user_task: str, task_name: str) -> bool:
        self.socketio.emit('map_confirmation', {'msg': f"I think that '{user_task}' is the action '{task_name}'. Is that right?"})
        print("message emitted")
        self.response_event.wait() 
        return self.response

if __name__ == '__main__':
    interface = WebInterface()
    #result=interface.request_user_task()
    def delayed_task():
        interface.request_user_task()
    threading.Timer(5, delayed_task).start()