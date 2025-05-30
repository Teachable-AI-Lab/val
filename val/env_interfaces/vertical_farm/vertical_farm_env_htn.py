# val/env_interfaces/vertical_farm/vertical_farm_htn_methods.py
from time import sleep
from typing import Tuple, Dict, List, Any, Set
import argparse
import requests
import json

import websocket
from websockets.sync.client import connect
from uuid import uuid4
from json import dumps, loads

from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx
from pyhtn.conditions.fact import Fact
from pyhtn.conditions.pattern_matching import Filter
from pyhtn.domain.variable import V


class VerticalFarmHTNEnv(object):
    def __init__(self, base_url: str,
                 agent_id: str,
                 puppet_id: str,
                 priority: int = 128,
                 session_id: str = None,
                 transaction_ids: bool = False):
        self.url = base_url

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

    def get_state_from_game(self):
        state = self._send({"command": "get_state"})
        return state

    def get_state(self) -> List[Dict[str, Any]]:
        """
        Fetches the raw state via get_state_from_game(), flattens nested structures
        into atomic facts, and assigns each fact a unique 'id'.
        """
        raw = self.get_state_from_game()
        if not raw or raw.get('code') != 2001:
            raise RuntimeError("Failed to retrieve state from game")

        content = raw['content']
        info = content.get('info', {})
        percept = content.get('percept', [])

        val_state: List[Dict[str, Any]] = []
        bot_id = info.get('puppet_id')

        # 1) Flatten bot info
        for key, val in info.items():
            if key == 'reservoir' and isinstance(val, dict):
                # one fact per chemical
                for chem, amount in val.items():
                    val_state.append({
                        'entity': bot_id,
                        'reservoir_chem': chem,
                        'amount': amount
                    })
            elif isinstance(val, list):
                # one fact per list element
                for item in val:
                    val_state.append({
                        'entity': bot_id,
                        key: item
                    })
            else:
                # simple scalar fact
                val_state.append({
                    'entity': bot_id,
                    key: val
                })

        # 2) Flatten percept (grid cells)
        for cell in percept:
            cell_id = f"{cell['x']}_{cell['y']}_{cell['floor']}"

            # Handle station cells separately (no saturation/plant_count)
            if cell['cell_type'] == 'station':
                val_state.append({
                    'entity': cell_id,
                    'cell_type': cell['cell_type'],
                    'station_type': cell.get('station_type'),
                    'bot_on_grid': cell['bot_on_grid']
                })
            else:
                print(cell)
                # Soil (or other) cells include saturation & plant_count
                val_state.append({
                    'entity': cell_id,
                    'cell_type': cell['cell_type'],
                    'bot_on_grid': cell['bot_on_grid'],
                    'saturation': cell['saturation'],
                    'plant_count': cell['plant_count']
                })
                # One fact per plant in this soil cell
                for plant in cell.get('plants', []):
                    val_state.append({
                        'entity': cell_id,
                        'plant_species': plant.get('species'),
                        'growth_stage': plant.get('growth_stage')
                    })

        # 3) High-level flag: any ripe plants?
        ripe_ready = any(
            p.get('growth', 0) >= 1.0
            for cell in percept
            for p in (cell.get('plants') or [])
        )
        val_state.append({'ripe_ready': ripe_ready})

        # 4) Assign unique IDs
        if not hasattr(self, 'id_count'):
            self.id_count = 0
        if not hasattr(self, 'count'):
            self.count = 0

        for entry in val_state:
            if 'entity' in entry and entry['entity'] != bot_id:
                entry_id = entry['entity']
            elif 'reservoir_chem' in entry:
                entry_id = entry['reservoir_chem']
            else:
                entry_id = self.id_count
                self.id_count += 1
            entry['id'] = entry_id

        # 5) Snapshot counter (optional)
        self.count += 1
        print(f"[VerticalFarmHTN] snapshot # {self.count}")

        print(val_state)

        return val_state



    def execute_plan(self, plan_seq: list) -> dict:
        return self._send({"command": "execute_plan", "plan": plan_seq})

    def send_and_recv(self, message: dict):
        sleep(0.25)
        message = json.dumps(message)
        attempts = 0
        while attempts < 3:
            try:
                self.ws.send(message)
                result = self.ws.recv()
                return json.loads(result)
            except:
                print(attempts)
                attempts = attempts + 1
                self.ws = websocket.create_connection(self.url)

        print("Failed")
        return None

    def get_objects(self) -> List[str]:
        """
        Returns a list of unique object identifiers present in the current state.
        """
        state = self.get_state()
        objects: Set[str] = set()
        for fact in state:
            # gather each entity as an object
            if 'entity' in fact:
                objects.add(fact['entity'])
            # include any other keys that represent objects, if needed
        print(objects)
        return list(objects)

    def get_actions(self) -> List[Tuple[str, List[str]]]:
        domain = {}
        descriptions = {}

        # ── 1) Primitive operators ────────────────────────────────────────────

        # Move one step in a cardinal direction (up/down/left/right)
        domain["move"] = [
            Operator(
                name="move",
                args=[V("direction")],
                preconditions=Fact(current_actions=V("move")),
                effects=[]
            )
        ]
        descriptions["move"] = "Move the farm bot one cell in the given direction."

        # Teleport or path‐plan to exact coordinates
        domain["move_to"] = [
            Operator(
                name="move_to",
                args=[V("x"), V("y")],
                preconditions=Fact(sensing_range_x=V("rx")) & Fact(sensing_range_y=V("ry")),
                effects=[]
            )
        ]
        descriptions["move_to"] = "Move the farm bot directly to coordinates (x,y)."

        # Interact with whatever is in the current cell (station or plot)
        domain["interact"] = [
            Operator(
                name="interact",
                args=[],
                preconditions=Fact(current_actions=V("interact")),
                effects=[]
            )
        ]
        descriptions["interact"] = "Interact with the station or plot you’re standing on."

        # The core farming primitives
        for op in ["sample", "spray", "harvest", "pluck", "pick_up", "put_down", "plant", "till"]:
            domain[op] = [
                Operator(
                    name=op,
                    args=[V("target")],
                    preconditions=Fact(full_actions=V(op)),
                    effects=[]
                )
            ]
            descriptions[op] = f"Perform '{op}' on the given target."

        # ── 2) Macro methods (“recipes”) ─────────────────────────────────────

        # PLANT: pick up a seed and plant it in a plot
        domain["plant"] = [
            Method(
                name="plant",
                # bind: seed type, plot ID, station coords, plot coords
                args=[V("seed"), V("plot"), V("sx"), V("sy"), V("px"), V("py")],
                preconditions=(
                    # you have the seed type in your reservoir
                        Fact(reservoir_chem=V("seed")) &
                        # the plot really is a soil cell
                        Fact(cell_type=V("soil")) &
                        # fetch coordinates for both station & plot
                        Fact(cell_id=V("plot")) & Fact(x=V("px")) & Fact(y=V("py")) &
                        Fact(x=V("sx")) & Fact(y=V("sy"))
                ),
                subtasks=[
                    # go to the planting station
                    Task("move_to", V("sx"), V("sy")),
                    Task("interact"),  # pick up a seed
                    # go to the chosen plot
                    Task("move_to", V("px"), V("py")),
                    Task("plant", V("plot"))
                ]
            )
        ]
        descriptions["plant"] = (
            "Move to the PlantStation (at ?sx,?sy), grab a seed, "
            "then move to the soil plot (at ?px,?py) and plant it."
        )

        domain["move_around"] = [
            Method(
                name="move_around",
                args=[],
                preconditions=Fact(current_actions=V("move")),
                subtasks=[
                    Task("move", "up"),
                    Task("move", "right"),
                    Task("move", "down"),
                    Task("move", "left")
                ]
            )
        ]
        descriptions["move_around"] = (
            "Move one cell up, then right, then down, then left (a patrol loop)."
        )



        # WATER: refill water and irrigate a plot
        domain["water"] = [
            Method(
                name="water",
                args=[V("plot")],
                preconditions=Fact(reservoir_chem=V("w")),
                subtasks=[
                    Task("move_to", "WaterStation"),
                    Task("interact"),  # refill water
                    Task("move_to", V("plot_x"), V("plot_y")),
                    Task("spray", V("w"))
                ]
            )
        ]
        descriptions["water"] = "move_to the water station, refill, then irrigate the target plot."

        # HARVEST: collect produce and deposit it
        domain["harvest"] = [
            Method(
                name="harvest",
                args=[V("plot")],
                preconditions=Fact(plant_count=V("n")) & Filter(lambda n: n > 0),
                subtasks=[
                    Task("move_to", V("plot_x"), V("plot_y")),
                    Task("harvest", V("plot")),  # pick the crop
                    Task("move_to", "CollectionStation"),
                    Task("interact")  # drop it off
                ]
            )
        ]
        descriptions["harvest"] = "Move to a ripe plot, harvest it, then deliver produce to the collection station."

        # TILL: prepare soil for planting
        domain["till"] = [
            Method(
                name="till",
                args=[V("plot")],
                preconditions=Fact(cell_type=V("soil")) & Fact(plant_count=V("0")),
                subtasks=[
                    Task("move_to", V("plot_x"), V("plot_y")),
                    Task("till", V("plot"))
                ]
            )
        ]
        descriptions["till"] = "Move to an empty soil plot and till the ground for planting."

        # SAMPLE: take a soil sample
        domain["sample"] = [
            Method(
                name="sample",
                args=[V("plot")],
                preconditions=Fact(cell_type=V("soil")),
                subtasks=[
                    Task("move_to", V("plot_x"), V("plot_y")),
                    Task("sample", V("plot"))
                ]
            )
        ]
        descriptions["sample"] = "Move to a soil plot and collect a sample for analysis."

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

    def move_to(self, x: Any, y: Any) -> bool:
        resp = self._send({"command": "move_to", "x": x, "y": y})
        return resp.get("success", False)

    def move(self, direction: str) -> bool:
        resp = self._send({"command": "move", "direction": direction})
        return resp.get("success", False)

    def interact(self) -> bool:
        resp = self._send({"command": "interact"})
        return resp.get("success", False)

    def sample(self, target: Any) -> bool:
        resp = self._send({"command": "sample", "target": target})
        return resp.get("success", False)

    def spray(self, volume: Any) -> bool:
        resp = self._send({"command": "spray", "volume": volume})
        return resp.get("success", False)

    def harvest(self, target: Any) -> bool:
        resp = self._send({"command": "harvest", "target": target})
        return resp.get("success", False)

    def pluck(self, target: Any) -> bool:
        resp = self._send({"command": "pluck", "target": target})
        return resp.get("success", False)

    def pick_up(self) -> bool:
        resp = self._send({"command": "pick_up"})
        return resp.get("success", False)

    def put_down(self) -> bool:
        resp = self._send({"command": "put_down"})
        return resp.get("success", False)

    def plant(self, target: Any) -> bool:
        resp = self._send({"command": "plant", "target": target})
        return resp.get("success", False)

    def till(self) -> bool:
        resp = self._send({"command": "till"})
        return resp.get("success", False)

    def execute_action(self, action_name: str, args: List[Any]) -> bool:
        """
        Dispatch HTN primitive actions by sending a JSON 'execute_action' command
        with named params and an API key via WebSocket.
        """
        if isinstance(args, tuple):
            args = list(args)
        print(f"[ENV] Executing: {action_name}({args})")

        param_map = {
            'move': (['direction'], {'direction': str}),
            'move_to': (['x', 'y'], {'x': int, 'y': int}),
            'interact': ([], {}),
            'sample': (['target'], {'target': int}),
            'spray': (['volume'], {'volume': float}),
            'harvest': (['target'], {'target': int}),
            'pluck': (['target'], {'target': int}),
            'pick_up': ([], {}),
            'put_down': ([], {}),
            'plant': (['target'], {'target': int}),
            'till': ([], {})
        }

        names, types = param_map.get(action_name, ([], {}))

        # Build params dict
        params = {}
        for i, name in enumerate(names):
            if i < len(args):
                value = args[i]
                # optionally cast: value = types.get(name, lambda x: x)(value)
                params[name] = value

        msg = {
            "command": "execute_action",
            "action": action_name,
            "params": params,
            "api_key": self.api_key
        }
        result = self._send(msg)
        if not result:
            return False
        status = result.get('status') or result.get('Status') or ''
        return status.lower() in ("ok", "success")

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
