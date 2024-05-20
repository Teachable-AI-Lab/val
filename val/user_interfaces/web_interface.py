import socketio
from socketio.exceptions import TimeoutError

class WebInterface:
    def __init__(self, url="http://localhost:4000"):
        self.sio = socketio.SimpleClient()
        self.sio.connect('http://localhost:4000')

    def display_known_tasks(self, tasks):
        pass

    def request_user_task(self) -> str:
        self.sio.emit('message', {'type': 'request_user_task', 
                                  'text': 'How can I help you today?'})
        print("The message is emitted")

        try:
            print('waiting for response')
            event = self.sio.receive(timeout=120)
        except TimeoutError:
            print('timed out waiting for event')
        else:
            print('received event:', event)

        return ""
    
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
    result=interface.request_user_task()
    # def delayed_task():
    #     interface.request_user_task()
    # threading.Timer(5, delayed_task).start()
