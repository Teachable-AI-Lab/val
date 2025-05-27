# val/env_interfaces/vertical_farm/vertical_farm_htn_methods.py
from typing import Tuple, Dict, List

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

from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx
from pyhtn.conditions.fact import Fact
from pyhtn.conditions.conditions import NOT
from pyhtn.domain.variable import V

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

    def get_actions(self) -> List[Tuple[str, List[str]]]:
        domain = {}
        descriptions = {}

        domain["move"] = [
            Operator(
                name="move",
                args=(V("direction"),),
                preconditions=Fact(current_actions=V("actions")) &
                              Filter(lambda actions, direction: direction in actions),
                effects=[]
            )
        ]
        descriptions["move"] = "Move puppet one step in the given direction."

        domain["move_to"] = [
            Operator(
                name="move_to",
                args=(V("x"), V("y")),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "move_to" in actions),
                effects=[]
            )
        ]
        descriptions["move_to"] = "Move puppet to coordinates (x, y)."

        domain["interact"] = [
            Operator(
                name="interact",
                args=(),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "interact" in actions),
                effects=[]
            )
        ]
        descriptions["interact"] = "Interact with an adjacent object."

        domain["pick"] = [
            Operator(
                name="pick",
                args=(V("target"),),
                preconditions=Fact(current_actions=V("actions")) &
                              Filter(lambda actions: "pick" in actions) &
                              Fact(stage=V("stage")) &
                              Filter(lambda stage: stage == "fruiting"),
                effects=[]
            )
        ]
        descriptions["pick"] = "Pick fruit at target slot (must be fruiting)."

        domain["pick_up"] = [
            Operator(
                name="pick_up",
                args=(),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "pick_up" in actions),
                effects=[]
            )
        ]
        descriptions["pick_up"] = "Pick up an object at current location."

        domain["put_down"] = [
            Operator(
                name="put_down",
                args=(),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "put_down" in actions),
                effects=[]
            )
        ]
        descriptions["put_down"] = "Put down carried object."

        domain["harvest"] = [
            Operator(
                name="harvest",
                args=(V("target"),),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "harvest" in actions),
                effects=[]
            )
        ]
        descriptions["harvest"] = "Harvest the crop at target slot."

        domain["pluck"] = [
            Operator(
                name="pluck",
                args=(V("target"),),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "pluck" in actions),
                effects=[]
            )
        ]
        descriptions["pluck"] = "Pluck fruit at target slot."

        domain["sample"] = [
            Operator(
                name="sample",
                args=(V("target"),),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "sample" in actions),
                effects=[]
            )
        ]
        descriptions["sample"] = "Take a sample from target slot."

        domain["spray"] = [
            Operator(
                name="spray",
                args=(V("volume"),),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "spray" in actions),
                effects=[]
            )
        ]
        descriptions["spray"] = "Spray fertilizer or pesticide of given volume."

        domain["plant"] = [
            Operator(
                name="plant",
                args=(V("target"),),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "plant" in actions),
                effects=[]
            )
        ]
        descriptions["plant"] = "Plant a seed at target slot."

        domain["till"] = [
            Operator(
                name="till",
                args=(),
                preconditions=Fact(current_actions=V("actions")) & Filter(lambda actions: "till" in actions),
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
    base_url = "http://localhost:4649"
    agent_id = "agent123"
    puppet_id = "farm_bot_1"

    # Initialize the HTN environment
    env = VerticalFarmHTNEnv(
        base_url=base_url,
        agent_id=agent_id,
        puppet_id=puppet_id
    )

    # 1. Fetch and print current state
    state = env.get_state()
    print("Current state:", state)

    # 2. Fetch and print available actions and their descriptions
    domain, descriptions = env.get_actions()
    print("Action domain:", domain)
    print("Descriptions:", descriptions)

    # 3. Execute individual actions
    print("Move up:", env.execute_action("move", {"direction": "up"}))
    print("Interact:", env.execute_action("interact", None))
    print("Plant seed in plant_slot_1:", env.execute_action("plant", {"target": "plant_slot_1"}))
    print("pick", env.execute_action("pick", {"target": "plant_slot_1"}))
    print("Harvest plant_slot_1:", env.execute_action("harvest", {"target": "plant_slot_1"}))
    print("Till the soil:", env.execute_action("till", None))
    print("Spray fertilizer with volume 10:", env.execute_action("spray", {"volume": 10}))

    # 4. Or dispatch a small HTN plan
    plan = [
        ["move", "up"],
        ["interact"],
        ["move", "left"],
        ["harvest", "plant_slot_1"]
    ]
    results = env.run_tasks(plan)
    print("Plan execution results:", results)

