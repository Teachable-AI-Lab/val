# val/env_interfaces/vertical_farm/vertical_farm_htn_methods.py
from shop2.domain import Operator, Fact, Filter
from shop2.domain import Task
from shop2.common import V
from shop2.planner import planner
import argparse
import requests
import json
from websockets.sync.client import connect
from uuid import uuid4
from json import dumps, loads

class VerticalFarmHTNEnv(object):
    def __init__(self, base_url: str,
                 agent_id: str,
                 puppet_id: str,
                 priority: int = 128,
                 session_id: str = None,
                 transaction_ids: bool = False):
        # Normalize and store connection parameters
        self.base_url = base_url.rstrip('/')
        self.agent_id = agent_id
        self.puppet_id = puppet_id
        self.priority = priority
        self.session_id = session_id
        self.transaction_ids = transaction_ids

        # register agent
        data = {"agent_id": agent_id, "puppet_id": puppet_id}
        if priority is not None:   data["priority"] = priority
        if session_id is not None: data["session_id"] = session_id
        resp = requests.post(f"{self.base_url}/register_agent", json=data)
        resp.raise_for_status()
        info = resp.json()
        self.service_target = info['service_target']
        self.api_key = info.get('api_key', '')
        self.connection = connect(self.service_target,
                                  open_timeout=None, close_timeout=None)

    _TASK_DISPATCH = {
        'stop':    lambda env, args: env.execute_action('stop',    None),
        'hold':    lambda env, args: env.execute_action('hold',    None),
        'move':    lambda env, args: env.execute_action('move',    {'direction': args[0]}),
        'move_to': lambda env, args: env.execute_action('move_to', {'x': args[0], 'y': args[1]}),
        'interact':lambda env, args: env.execute_action('interact', None),
        'pick_up': lambda env, args: env.execute_action('pick_up', None),
        'put_down':lambda env, args: env.execute_action('put_down',None),
        'harvest': lambda env, args: env.execute_action('harvest', {'target': args[0]}),
        'pluck':   lambda env, args: env.execute_action('pluck',   {'target': args[0]}),
        'sample':  lambda env, args: env.execute_action('sample',  {'target': args[0]}),
        'spray':   lambda env, args: env.execute_action('spray',   {'volume': args[0]}),
        'plant':   lambda env, args: env.execute_action('plant',   {'target': args[0]}),
        'till':    lambda env, args: env.execute_action('till',    None),
    }


    @staticmethod
    def list_puppets(base_url: str):
        """
        Fetches and prints all puppet IDs from the agent service.
        """
        if not base_url.startswith('http'):
            base_url = f'http://{base_url}'
        resp = requests.get(f'{base_url}/list_puppets')
        resp.raise_for_status()
        puppets = resp.json().get('puppets', [])
        for p in puppets:
            print('-', p['puppet_id'])

    def _send(self, msg: dict) -> dict:
        if self.api_key:
            msg['api_key'] = self.api_key
        if self.transaction_ids:
            msg['transaction_id'] = str(uuid4())
        payload = dumps(msg)
        self.connection.send(payload)
        return loads(self.connection.recv())

    def get_state(self) -> dict:
        return self._send({"command": "get_state"})

    def execute_action(self, action: str, params: dict = None) -> dict:
        cmd = {"command": "execute_action", "action": action}
        if params: cmd["params"] = params
        return self._send(cmd)

    def execute_plan(self, plan_seq: list) -> dict:
        return self._send({"command": "execute_plan", "plan": plan_seq})

    def get_vertical_farm_actions(self):
        domain = {}
        descriptions = {}

        domain["stop/0"] = [
            Operator(
                head=('stop',),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'stop' in actions),
                effects=[]
            )
        ]
        descriptions["stop/0"] = "Stop the puppet immediately."

        domain["hold/0"] = [
            Operator(
                head=('hold',),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'hold' in actions),
                effects=[]
            )
        ]
        descriptions["hold/0"] = "Pause puppet until further instruction."

        domain["move/1"] = [
            Operator(
                head=('move', V('direction')),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions, direction: direction in actions),
                effects=[]
            )
        ]
        descriptions["move/1"] = "Move puppet one step in the given direction."

        domain["move_to/2"] = [
            Operator(
                head=('move_to', V('x'), V('y')),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'move_to' in actions),
                effects=[]
            )
        ]
        descriptions["move_to/2"] = "Move puppet to coordinates (x, y)."

        domain["interact/0"] = [
            Operator(
                head=('interact',),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'interact' in actions),
                effects=[]
            )
        ]
        descriptions["interact/0"] = "Interact with an adjacent object."

        domain["pick_up/0"] = [
            Operator(
                head=('pick_up',),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'pick_up' in actions),
                effects=[]
            )
        ]
        descriptions["pick_up/0"] = "Pick up an object at current location."

        domain["put_down/0"] = [
            Operator(
                head=('put_down',),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'put_down' in actions),
                effects=[]
            )
        ]
        descriptions["put_down/0"] = "Put down carried object."

        domain["harvest/1"] = [
            Operator(
                head=('harvest', V('target')),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'harvest' in actions),
                effects=[]
            )
        ]
        descriptions["harvest/1"] = "Harvest the crop at target slot."

        domain["pluck/1"] = [
            Operator(
                head=('pluck', V('target')),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'pluck' in actions),
                effects=[]
            )
        ]
        descriptions["pluck/1"] = "Pluck fruit at target slot."

        domain["sample/1"] = [
            Operator(
                head=('sample', V('target')),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'sample' in actions),
                effects=[]
            )
        ]
        descriptions["sample/1"] = "Take a sample from target slot."

        domain["spray/1"] = [
            Operator(
                head=('spray', V('volume')),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'spray' in actions),
                effects=[]
            )
        ]
        descriptions["spray/1"] = "Spray fertilizer or pesticide of given volume."

        domain["plant/1"] = [
            Operator(
                head=('plant', V('target')),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'plant' in actions),
                effects=[]
            )
        ]
        descriptions["plant/1"] = "Plant a seed at target slot."

        domain["till/0"] = [
            Operator(
                head=('till',),
                preconditions=Fact(current_actions=V('actions')) & Filter(lambda actions: 'till' in actions),
                effects=[]
            )
        ]
        descriptions["till/0"] = "Till the soil in front of puppet."

        return domain, descriptions

    def run_tasks(self, tasks: list) -> list:
        """
        Execute HTN tasks [ [name, *args], ... ] by dispatching directly to execute_action.
        """
        results = []
        for task in tasks:
            name, *args = task
            handler = self._TASK_DISPATCH.get(name)
            if handler is None:
                raise ValueError(f'unmapped task: {name}')
            results.append(handler(self, args))
        return results


if __name__ == "__main__":
    import argparse, json, sys

    parser = argparse.ArgumentParser(prog='Test Vertical Farm HTN')
    parser.add_argument('base_url', help='e.g. http://localhost:4649')
    parser.add_argument('agent_id')
    parser.add_argument('puppet_id')
    parser.add_argument('--tasks',
                        default='[["move", "up"], ["stop"]]',
                        help='JSON list of HTN tasks')
    parser.add_argument('--list-puppets', action='store_true', dest='list_puppets',
                        help='Print available puppet IDs')
    args = parser.parse_args()

    if args.list_puppets:
        VerticalFarmHTNEnv.list_puppets(args.base_url)
        sys.exit(0)


    if args.list_puppets:
        VerticalFarmHTNEnv.list_puppets(args.base_url)
        sys.exit(0)

    try:
        htn_env = VerticalFarmHTNEnv(
            base_url=args.base_url,
            agent_id=args.agent_id,
            puppet_id=args.puppet_id
        )
    except Exception as e:
        print("Failed to initialize HTN environment:", e)
        sys.exit(1)

    tasks = json.loads(args.tasks)
    results = htn_env.run_tasks(tasks)
    print("Task results:", results)