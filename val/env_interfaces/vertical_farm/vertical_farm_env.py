import sys
import websocket
import importlib
import json
import math
import requests
from json.decoder import JSONDecodeError
from uuid import uuid4
import argparse
import random
import time
from pprint import pprint

class VerticalFarmEnv:
    """
    Client for interacting with the Vertical Farm puppetry server
    using HMT Puppetry API 2.0 (Vertical Farm spec).
    """

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

        # Filled in on registration
        self.api_key = None
        self.service_target = None
        self.ws = None

        self._register_agent()

    def _register_agent(self):
        """
        Register this agent with the puppetry server.
        Populates api_key, session_id, service_target, and opens websocket.
        """
        url = f"{self.base_url}/register_agent"
        payload = {
            "agent_id": self.agent_id,
            "puppet_id": self.puppet_id,
            "priority": self.priority,
        }
        if self.session_id:
            payload["session_id"] = self.session_id

        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        # Extract handshake values
        self.service_target = data["service_target"]
        self.api_key = data.get("api_key")
        self.session_id = data.get("session_id", self.session_id)

        # Open WebSocket connection
        self.ws = websocket.create_connection(self.service_target)

    def list_puppets(self) -> list:
        """
        Retrieve global list of available puppets via HTTP.
        """
        url = f"{self.base_url}/list_puppets"
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("puppets", [])

    def _send(self, message: dict, retries: int = 3) -> dict:
        """
        Send a JSON command over WebSocket and await a JSON response.
        Retries a failed send up to `retries` times.
        Automatically injects api_key and optional transaction_id.
        """
        if not self.ws:
            raise ConnectionError("WebSocket is not connected")

        msg = message.copy()
        if self.api_key:
            msg["api_key"] = self.api_key
        if self.transaction_ids:
            msg["transaction_id"] = str(uuid4())

        payload = json.dumps(msg)
        for attempt in range(retries):
            try:
                self.ws.send(payload)
                resp = self.ws.recv()
                return json.loads(resp)
            except Exception:
                if attempt < retries - 1:
                    self.ws = websocket.create_connection(self.service_target)
                else:
                    raise

    def get_state(self) -> dict:
        """
        Retrieve current state of the puppet.
        """
        return self._send({"command": "get_state"})

    def execute_action(self, action: str, params: dict = None) -> dict:
        """
        Send a single action command to the puppet.
        """
        cmd = {"command": "execute_action", "action": action}
        if params:
            cmd["params"] = params
        return self._send(cmd)

    def execute_plan(self, plan: list) -> dict:
        cmd = {"command": "execute_plan", "plan": plan}
        return self._send(cmd)

    def stop(self) -> bool:
        resp = self.execute_action("stop")
        return resp.get("code") == 2000

    def hold(self) -> bool:
        resp = self.execute_action("hold")
        return resp.get("code") == 2000

    def move(self, direction: str) -> bool:
        resp = self.execute_action("move", {"direction": direction})
        return resp.get("code") == 2000

    def move_to(self, x: int, y: int) -> bool:
        resp = self.execute_action("move_to", {"x": x, "y": y})
        return resp.get("code") == 2000

    def interact(self) -> bool:
        resp = self.execute_action("interact")
        return resp.get("code") == 2000

    def pick_up(self) -> bool:
        resp = self.execute_action("pick_up")
        return resp.get("code") == 2000

    def put_down(self) -> bool:
        resp = self.execute_action("put_down")
        return resp.get("code") == 2000

    def harvest(self, target: int = None) -> bool:
        params = {"target": target} if target is not None else None
        resp = self.execute_action("harvest", params)
        return resp.get("code") == 2000

    def pluck(self, target: int = None) -> bool:
        params = {"target": target} if target is not None else None
        resp = self.execute_action("pluck", params)
        return resp.get("code") == 2000

    def sample(self, target: int = None) -> bool:
        params = {"target": target} if target is not None else None
        resp = self.execute_action("sample", params)
        return resp.get("code") == 2000

    def spray(self, volume: int) -> bool:
        resp = self.execute_action("spray", {"volume": volume})
        return resp.get("code") == 2000

    def plant(self, target: int) -> bool:
        resp = self.execute_action("plant", {"target": target})
        return resp.get("code") == 2000

    def till(self) -> bool:
        resp = self.execute_action("till")
        return resp.get("code") == 2000


    def find_nearest_target(self):
        state = self.get_state().get('content', {})
        # TODO: implement pathfinding logic
        raise NotImplementedError("Nearest-target logic not implemented")



def test_random_walk(env: VerticalFarmEnv, wait_time=1, iterations=None, full_response=False):
    directions = ["up", "down", "left", "right"]
    it = 0
    while iterations is None or it < iterations:
        print(f"Iteration: {it}")
        state = env.get_state()
        if full_response:
            pprint(state)
        else:
            print(state.get('puppet_id'), state.get('command'), state.get('code'))

        move_dir = random.choice(directions)
        resp = env.execute_action("move", {"direction": move_dir})
        if full_response:
            pprint(resp)
        else:
            print(resp.get('puppet_id'), resp.get('command'), resp.get('code'))

        time.sleep(wait_time)
        it += 1


def test_random(env: VerticalFarmEnv, wait_time=1, iterations=None, full_response=False):
    directions = ["up", "down", "left", "right"]
    it = 0
    while iterations is None or it < iterations:
        print(f"Iteration: {it}")
        state = env.get_state()
        info = state.get('content', {}).get('info', {})
        actions = info.get('current_actions') or info.get('full_actions', [])
        if not actions:
            print('No available actions; stopping.')
            break
        if full_response:
            pprint(state)
        else:
            print(state.get('puppet_id'), state.get('command'), state.get('code'))

        act = random.choice(actions)
        if act == 'move':
            dir_choice = random.choice(directions)
            resp = env.execute_action(act, {"direction": dir_choice})
        else:
            resp = env.execute_action(act)

        if full_response:
            pprint(resp)
        else:
            print(resp.get('puppet_id'), resp.get('command'), resp.get('code'))

        time.sleep(wait_time)
        it += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Test Agent',
        description='A simple agent for testing the HMT Agent Interface')

    parser.add_argument(
        'root_url', help='The root url for the agent service, e.g. localhost:4649')
    parser.add_argument('-l', '--list_puppets', action='store_true',
                        help='Overrides other params and calls the list_puppets API')
    parser.add_argument('-p', '--puppet_id', help='The puppet_id to register actions on')
    parser.add_argument('-a', '--agent_id', default='TEST',
                        help='The agent id to register, can be any string')
    parser.add_argument('-r', '--priority', type=int, default=128,
                        help='The priority for actions')
    parser.add_argument('-s', '--style', choices=['random-walk', 'random', 'action'],
                        default='random-walk', help='Testing style')
    parser.add_argument('-w', '--wait_time', type=float, default=1.0,
                        help='Seconds between actions')
    parser.add_argument('-i', '--iterations', type=int, default=None,
                        help='Number of actions; infinite if omitted')
    parser.add_argument('-f', '--full_response', action='store_true',
                        help='Print full JSON responses')
    parser.add_argument('-t', '--send_transaction_ids', action='store_true',
                        help='Include transaction IDs in messages')
    parser.add_argument('-x', '--action', help='Specific action to test (e.g. move, harvest)')
    parser.add_argument('--params', help='JSON string of params for the action')

    args = parser.parse_args()
    root = args.root_url
    if not root.startswith('http'):
        root = 'http://' + root

    if args.list_puppets:
        # Directly call the HTTP endpoint without registering agent
        try:
            resp = requests.get(f"{root}/list_puppets")
            resp.raise_for_status()
            data = resp.json()
            print("Retrieved Puppets:")
            for p in data.get('puppets', []):
                print(f" - {p.get('puppet_id')} : {p.get('action_set')}")
        except requests.HTTPError as e:
            print('Error retrieving puppets:', e)
        sys.exit(0)
    else:
        print('Unknown style')
        sys.exit(1)
