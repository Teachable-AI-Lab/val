import socketio
from socketio.exceptions import TimeoutError
from typing import List
from typing import Optional

from val.utils import Task
from val.user_interfaces.abstract_interface import AbstractUserInterface

class WebInterface(AbstractUserInterface):

    def __init__(self, url="http://localhost:4000",
                 disable_segment_confirmation: bool = False, disable_map_confirmation: bool = False,
                 disable_map_correction: bool = False, disable_map_new_method_confirmation: bool = False, 
                 disable_ground_confirmation: bool = False, disable_ground_correction: bool = False,
                 disable_gen_confirmation: bool = False, disable_gen_correction: bool = False,
                 disable_confirm_task_decomposition: bool = False, disable_confirm_task_execution: bool = False):
        self.sio = socketio.SimpleClient()
        self.sio.connect(url)
        self.disable_segment_confirmation = disable_segment_confirmation
        self.disable_map_confirmation = disable_map_confirmation
        self.disable_map_correction = disable_map_correction
        self.disable_map_new_method_confirmation = disable_map_new_method_confirmation
        self.disable_ground_confirmation = disable_ground_confirmation
        self.disable_ground_correction = disable_ground_correction
        self.disable_gen_confirmation = disable_gen_confirmation
        self.disable_gen_correction = disable_gen_correction
        self.disable_confirm_task_decomposition = disable_confirm_task_decomposition
        self.disable_confirm_task_execution = disable_confirm_task_execution
    
    def display_known_tasks(self, tasks: List[str]):
        text = "\n".join([f"({i}): {task}" for i, task in enumerate(tasks)])
        self.sio.emit('message', {'type': 'display_known_tasks',
                                  'text': "Those are the actions I know:" + text})
        return
        
    def request_user_task(self) -> str:
        self.sio.emit('message', {'type': 'request_user_task', 
                                  'text': 'How can I help you today?'})
        print("The message is emitted")

        # if you want timeout you can do something like this...
        # try:
        #     print('waiting for response')
        #     event = self.sio.receive(timeout=120)
        # except TimeoutError:
        #     print('timed out waiting for event')
        # else:
        #     print('received event:', event)

        print('waiting for response')
        event = self.sio.receive()
        print('received event:', event)
        return event[1]['response']
    
    def ask_subtasks(self, user_task: str) -> str:
        self.sio.emit('message', {'type': 'ask_subtasks', 
                                  'text': f"What are the steps for completing the task '{user_task}'?"})
        event = self.sio.receive()
        print('received event:', event)
        return event[1]['response']

    def ask_rephrase(self, user_tasks: str) -> str:
        self.sio.emit('message', {'type': 'ask_rephrase', 
                                  'text': f"Sorry about that. Can you rephrase the tasks '{user_tasks}'?"})
        event = self.sio.receive()
        print('received event:', event)
        return event[1]['response']

    def segment_confirmation(self, steps: List[str]) -> bool:
        if self.disable_segment_confirmation:
            return True 
        formatted_steps = ', '.join(steps)
        self.sio.emit('message', {'type': 'segment_confirmation', 
                                  'text': f"These are the individual steps of your command: '{formatted_steps}', right?",
                                  'steps': steps})
        event = self.sio.receive()
        print('received event:', event[1])
        return 'yes' == event[1]['response']

    def map_confirmation(self, user_task: str, task_name: str) -> bool:
        if self.disable_map_confirmation:
            return True 
        self.sio.emit('message', {'type': 'map_confirmation', 
                                  'text': f"I think that '{user_task}' is the action '{task_name}'. Is that right?"})
        event = self.sio.receive()
        print('received event:', event[1])
        return 'yes' == event[1]['response']

    def map_correction(self, user_task: str, known_tasks: List[str]) -> Optional[int]:
        known_tasks.append('None of these above')
        self.sio.emit('message', {'type': 'map_correction',
                                  'text': f"Which of these is the best choice for '{user_task}'?", 
                                  'user_task': user_task,
                                  'known_tasks': known_tasks})
        event = self.sio.receive()
        print('received event:', event)
        response = int(event[1]['response'])
        if response == len(known_tasks) - 1:
            print("none")
            return None
        return event[1]['response']

    def map_new_method_confirmation(self, user_task: str) -> bool:
        if self.disable_map_new_method_confirmation:
            return True
        self.sio.emit('message', {'type': 'map_new_method_confirmation',
                                  'text': f"The task '{user_task}' is a new method. Is that right?"})
        event = self.sio.receive()
        print('received event:', event)
        return 'yes' == event[1]['response']

    def ground_confirmation(self, task_name: str, task_args: List[str]) -> bool:
        if self.disable_ground_confirmation:
            return True 
        self.sio.emit('message', {'type': 'ground_confirmation',
                                  'text': f"The task is {task_name}({task_args}). Is that right?"})
        event = self.sio.receive()
        print('received event:', event)
        return 'yes' == event[1]['response']

    def ground_correction(self, task_name: str, task_args: List[str],
                          env_objects: List[str]) -> List[str]:
        self.sio.emit('message', {'type': 'ground_confirmation',
                                  'text': f"Could you help me pick the actual object? {task_name}",
                                  'task_args': task_args,
                                  'env_objects': env_objects})
        event = self.sio.receive()
        print('received event:', event)
        return event[1]['response']

    def gen_confirmation(self, user_task: str, task_name: str, task_args: List[str]) -> bool:
        if self.disable_gen_confirmation:
            return True
        formatted_args = ', '.join(task_args)
        self.sio.emit('message', {'type': 'gen_confirmation',
                                  'text': f"{user_task} is {task_name}({formatted_args}). Is that right?",
                                  'task_args': task_args})
        event = self.sio.receive()
        print('received event:', event)
        return 'yes' == event[1]['response']

    def gen_correction(self, task_name: str, task_args: List[str],
                       env_objects: List[str]) -> List[str]:
        self.sio.emit('message', {'type': 'gen_confirmation',
                                  'text': f"Could you help me pick the actual object? {task_name}:",
                                  'task_args': task_args,
                                  'env_objects': env_objects})
        event = self.sio.receive()
        print('received event:', event)
        return event[1]['response']

    def confirm_task_decomposition(self, user_task: str, user_subtasks: List[str]) -> bool:
        if self.disable_confirm_task_decomposition:
            return True
        self.sio.emit('message', {'type': 'ground_confirmation',
                                  'text': f"Should I decompose { user_task } to { user_subtasks }?"})
        event = self.sio.receive()
        print('received event:', event)
        return 'yes' == event[1]['response']

    def confirm_task_execution(self, user_task: str) -> bool:
        if self.disable_confirm_task_execution:
            return True
        self.sio.emit('message', {'type': 'ground_confirmation',
                                  'text': f"Should I execute { user_task }?"})
        event = self.sio.receive()
        print('received event:', event)
        return 'yes' == event[1]['response']
    


    
if __name__ == '__main__':
    interface = WebInterface()
    res1=interface.request_user_task()
    res2=interface.segment_confirmation(['go to the pot','press'])
    res=interface.map_confirmation('pot','go to the pot')
    #res2=interface.ask_subtasks(res1['message'])
    #res3=interface.map_correction("cook onion",["press space","move to"])
    # def delayed_task():
    #     interface.request_user_task()
    # threading.Timer(5, delayed_task).start()
