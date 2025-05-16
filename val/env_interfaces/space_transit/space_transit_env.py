import random
import time
from typing import List
from typing import Tuple
import sys
import websocket
import importlib
import json
import math

from nltk import edit_distance
from time import sleep
from pprint import pprint
from functools import partial

from pyhtn.htn import Operator, Method, Task
from pyhtn.conditions.fact import Fact
from pyhtn.domain.variable import V
from pyhtn.conditions.pattern_matching import Filter

class SpaceTransitEnv():

    def __init__(self, url='ws://localhost:3000/metro'):
        self.url = url
        self.ws = websocket.create_connection(self.url)
        self.line_names = ["redline", "blueline", "yellowline", "greenline", "purpleline"]
        self.active_game = 0
        # idk where to put this and might be worth discussing on where this should be long term.
        self.alerted_stations = dict()
        self.agent_id = random.randint(100000, 999999)

    def get_objects(self) -> List[str]:
        line_mapping, lines, stations = self.get_lines_and_stations()
        return list(stations.keys()) + list(line_mapping.keys())

    def get_actions(self) -> List[Tuple[str, List[str]]]:
        """ actions = []

        actions.append({"name": "create_line",
                        "args": ["?station1", "?station2"],
                        "description": "create a new line that connects station1 and station2",
                        "preconditions": [
                            {"type": "fact", "station": "?station1"},
                            {"type": "fact", "station": "?station2"},
                        ]})

        actions.append({"name": "delete_line",
                        "args": ["?line"],
                        "description": "delete the specified line",
                        "preconditions": [
                            {"type": "fact", "line": "?line"},
                        ]})

        actions.append({"name": "insert_station",
                        "args": ["?station", "?line"],
                        "description": "insert station to the given line",
                        "preconditions": [
                            {"type": "fact", "station": "?station"},
                            {"type": "fact", "line": "?line"},
                        ]})

        actions.append({"name": "remove_station",
                        "args": ["?station", "?line"],
                        "description": "remove the specified station from the given line",
                        "preconditions": [
                            {"type": "fact", "station": "?station"},
                            {"type": "fact", "line": "?line"},
                        ]})

        actions.append({"name": "goto_game",
                        "args": ["?game_id"],
                        "description": "go to a specific game with a given id",
                        "preconditions": [
                            {"type": "fact", "game": "?game_id"},
                        ]})
        
        actions.append({"name": "alert_station",
                        "args": ["?station_id"],
                        "description": "alerts the user that a specific station is timing out",
                        "preconditions": [
                            {"type": "fact", "station": "?station_id"},
                        ]})

        actions.append({"name": "add_train",
                        "args": ["?line"],
                        "description": "add train to the given line",
                        "preconditions": [
                            {"type": "fact", "line": "?line"},
                        ]})

        actions.append({"name": "remove_train",
                        "args": ["?line"],
                        "description": "remove train from the given line",
                        "preconditions": [
                            {"type": "fact", "line": "?line"},
                        ]})
        
        actions.append({"name": "wait_small",
                        "args": [],
                        "description": "waits for 1 second",
                        "preconditions": []})

        return actions """

        domain= {}
        descriptions = {}

        domain["create_line"] = [
            Operator(name='create_line',
                    args=[V('station1'), V('station2')],
                    preconditions=Fact(station=V('station1')) & Fact(station=V('station2')),
                    effects=[])
        ]
        descriptions["create_line"] = "create a new line that connects station1 and station2"

        domain["delete_line"] = [
            Operator(name='delete_line',
                    args=[V('line1')],
                    preconditions=Fact(line=V('line1')),
                    effects=[])
        ]
        descriptions["delete_line"] = "delete the specified line"

        domain["insert_station"] = [
            Operator(name='insert_station',
                    args=[V('station'), V('line')],
                    preconditions=Fact(station=V('station')) & Fact(line=V('line')),
                    effects=[])
        ]
        descriptions["insert_station"] = "insert station to the given line"

        domain["remove_station"] = [
            Operator(name='remove_station',
                    args=[V('station'), V('line')],
                    preconditions=Fact(station=V('station')) & Fact(line=V('line')),
                    effects=[])
        ]
        descriptions["remove_station"] = "remove the specified station from the given line"

        domain["goto_game"] = [
            Operator(name='goto_game',
                    args=[V('game_id')],
                    preconditions=Fact(game=V('game_id')),
                    effects=[])
        ]
        descriptions["goto_game"] = "go to a specific game with a given id"

        domain["alert_station"] = [
            Operator(name='alert_station',
                    args=[V('station_id')],
                    preconditions=Fact(station=V('station_id')),
                    effects=[])
        ]
        descriptions["alert_station"] = "alerts the user that a specific station is timing out"

        domain["add_train"] = [
            Operator(name='add_train',
                    args=[V('line1')],
                    preconditions=Fact(line=V('line1')),
                    effects=[])
        ]
        descriptions["add_train"] = "add train to the given line"

        domain["remove_train"] = [
            Operator(name='remove_train',
                    args=[V('line1')],
                    preconditions=Fact(line=V('line1')),
                    effects=[])
        ]
        descriptions["remove_train"] = "remove train to the given line"

        domain["wait_small"] = [
            Operator(name='wait_small',
                    args=[],
                    preconditions=Fact(),
                    effects=[])
        ]
        descriptions["wait_small"] = "waits for 1 sec"

        domain["connect_stations"] = [
            Method(name='connect_stations', # Changed from head=
                args=[],                # Added args
                preconditions=Fact(station=V('station1'), unique_id=V("uid1")) &
                                (~Fact(to_station=V("uid1")) & ~Fact(from_station=V("uid1"))) &
                                Fact(line=V("line")) &
                                Fact(any_lines=False),
                subtasks=[Task('insert_station', V('station1'), V('line')), Task('connect_stations')]),
            Method(name='connect_stations', # Changed from head=
                args=[],                # Added args
                preconditions=Fact(station=V('station1'), unique_id=V("uid1")) &
                                (~Fact(to_station=V("uid1")) & ~Fact(from_station=V("uid1"))) &
                                Fact(station=V('station2'), unique_id=V("uid2")) &
                                Fact(any_lines=True) &
                                Filter(lambda uid1, uid2: uid1 != uid2),
                subtasks=[Task('create_line', V('station1'), V('station2')), Task('connect_stations')]),
            Method(name='connect_stations', # Changed from head=
                args=[],                # Added args
                preconditions=Fact(agent_on=True),
                subtasks=[Task('wait_small'), Task('connect_stations')])
        ]
        descriptions["connect_stations"] = "connect all unconnected stations"

        domain["connect_nearest_stations"] = [
            Method(name='connect_nearest_stations', # Changed from head=
                args=[],                        # Added args
                preconditions=Fact(station_id=V('station1id'), nearest_station_id=V("station2id")) &
                                Fact(station=V('station1'), unique_id=V("station1id")) &
                                Fact(station=V('station2'), unique_id=V("station2id")) &
                                Fact(any_lines=True),
                subtasks=[Task('create_line', V('station1'), V('station2')), Task('connect_nearest_stations')]),
            Method(name='connect_nearest_stations', # Changed from head=
                args=[],                        # Added args
                preconditions=Fact(station_id=V('station1id'), nearest_station_id=V("station2id")) &
                                Fact(station=V('station1'), unique_id=V("station1id")) &
                                Fact(station=V('station2'), unique_id=V("station2id")) &
                                Fact(line=V("line"), id=V('lineId')) &
                                (Fact(to_station=V("station2id"), segment_line=V('lineId')) | Fact(from_station=V("station2id"), segment_line=V('lineId'))) &
                                Fact(any_lines=False),
                subtasks=[Task('insert_station', V('station1'), V('line')), Task('connect_nearest_stations')]), # Assuming connect_stations is still the desired recursive call
            Method(name='connect_nearest_stations', # Changed from head=
                args=[],                        # Added args
                preconditions=Fact(agent_on=True),
                subtasks=[Task('wait_small'), Task('connect_nearest_stations')]) # Assuming connect_stations is still the desired recursive call
        ]
        descriptions["connect_nearest_stations"] = "connect all unconnected stations to nearest unconnected"

        domain["remove_lines"] = [
            Method(name='remove_lines', # Changed from head=
                args=[],            # Added args
                preconditions=Fact(line=V('line'), line_id=V('uid')) &
                                Fact(segment_line=V('uid')),
                subtasks=[Task('delete_line', V('line')), Task('remove_lines')])
        ]
        descriptions["remove_lines"] = "delete all the lines"

        domain["connect_station_to_lines"] = [
            Method(name='connect_station_to_lines', # Changed from head=
                args=[V('station')],             # Added args (extracted from original head)
                preconditions=Fact(line=V('line'), line_id=V('uid')) &
                                Fact(station=V('station'), unique_id=V("uid1")) &
                                (~Fact(to_station=V("uid1"), segment_line=V('uid')) & ~Fact(from_station=V("uid1"), segment_line=V('uid'))),
                subtasks=[Task('insert_station', V('station'), V('line')), Task('connect_station_to_lines', V('station'))])
        ]
        descriptions["connect_station_to_lines"] = "Connects a station to all lines"

        domain["monitor_stations"] = [
            Method(name='monitor_stations', # Changed from head=
                args=[],                # Added args
                preconditions=Fact(station=V('station'), timer=V('timer')) &
                                Filter(lambda timer: timer != 0) &
                                Filter(lambda station: hasattr(self, 'is_valid_alert') and self.is_valid_alert(station)), # self refers to the context this function is called in
                subtasks=[Task('alert_station', V('station')), Task('monitor_stations')]),
            Method(name='monitor_stations', # Changed from head=
                args=[],                # Added args
                preconditions=Fact(agent_on=True),
                subtasks=[Task('wait_small'), Task('monitor_stations')])
        ]
        descriptions["monitor_stations"] = "checks all stations to see if any needs to be alerted."

        return domain, descriptions

    def get_state(self) -> dict:
        """
        Returns the state in a dict that can be converted into HTN representation.
        """
        val_state = []
        cur_state = self.get_state_from_game()

        with open('val\env_interfaces\space_transit\start.json', 'r') as f:
            data = json.load(f)
            val_state.append({'agent_on': data['start']})

        # line_mapping = {}
        lines = set()
        for line in cur_state['lines']:
            val_state.append({'line': self.line_names[line['id']], 'line_id': line['unique_id']})
            lines.add(line['unique_id'])
        
        seen_stations = set()

        for segment in cur_state['segments']:
            if segment['which_line'] not in val_state: #TODO debug
                val_state.append({'from_station': segment['from_station'],
                                  'to_station': segment['to_station'],
                                  'segment_line': segment['which_line']})
                seen_stations.add(segment['from_station'])
                seen_stations.add(segment['to_station'])
                if segment['which_line'] in lines:
                    lines.remove(segment['which_line'])

        for station in cur_state['stations']:
            val_state.append({'station': station['human_name'],
                              'unique_id': station['unique_id'],
                              'timer': station['timer']})
            if station['timer'] == 0 and station['human_name'] in self.alerted_stations.keys():
                self.alerted_stations[station['human_name']] = 0
            if station['unique_id'] not in seen_stations:
                closest_station = self.find_closest_station(cur_state['stations'], station)
                val_state.append({'station_id': station['unique_id'],
                                  'nearest_station_id': closest_station})


        
        val_state.append({'any_lines': len(lines)!=0})

        for i in range(len(val_state)):
            val_state[i]['id'] = self.agent_id


        return val_state
    
    def is_valid_alert(self, station):
        curr_time = time.time()
        if station not in self.alerted_stations.keys():
            self.alerted_stations[station] = curr_time
            return True
        if curr_time - self.alerted_stations[station] >= 30: #Number of seconds between alerts
            self.alerted_stations[station] = curr_time
            return True
        return False 
    
    def find_closest_station(self, station_list, comparison_station):
        min_dist = None
        id = -1
        for station in station_list:
            if station['unique_id'] == comparison_station['unique_id']:
                continue
            distance = math.sqrt(((station['x']-comparison_station['x'])**2)+((station['y']-comparison_station['y'])**2)+((station['z']-comparison_station['z'])**2))
            if min_dist is None or (distance<min_dist):
                min_dist = distance
                id = station['unique_id']
        
        return id
                

    def execute_action(self, action_name: str, args: List[str]) -> bool:
        if action_name == "create_line":
            return self.create_line(*args)
        elif action_name == "delete_line":
            return self.delete_line(*args)
        elif action_name == "insert_station":
            return self.insert_station(*args)
        elif action_name == "remove_station":
            return self.remove_station(*args)
        elif action_name == "goto_game":
            return self.goto_game(*args)
        elif action_name == "add_train":
            return self.add_train(*args)
        elif action_name == "remove_train":
            return self.remove_train(*args)
        elif action_name == "wait_small":
            return self.wait_small(*args)
        elif action_name == "alert_station":
            return self.alert_station(*args)
        raise Exception("No action matches. Please check action heads")

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

    def get_state_from_game(self):
        state = self.send_and_recv({"command":"get_state", "game_id": 0})
        #print("FIND ME")
        #print(state)
        return state

    def get_lines_and_stations(self):
        cur_state = self.get_state_from_game()
        line_mapping = {}
        for line in cur_state['lines']:
            line_mapping[self.line_names[line['id']]] = line['unique_id']

        lines = {}

        for segment in cur_state['segments']:
            if segment['which_line'] not in lines:
                lines[segment['which_line']] = [segment['from_station'], segment['to_station']]
            else:
                lines[segment['which_line']].append(segment['to_station'])

        stations = {station['human_name']: station for station in cur_state['stations']}

        return line_mapping, lines, stations

    def format_names(self, object_name, object_group):
        formatted_name = sorted([(edit_distance(name.lower(),
                                                object_name.lower()), name)
                                 for name in object_group])[0][1]
        return formatted_name
    
    def find_nearest_station_sameline(self, input_station, input_line):
    
        line_mapping, lines, stations = self.get_lines_and_stations()
        list_stations = list(stations.values()) # the value is a dict
        input_line_idx = line_mapping[input_line]
        stations_on_line = lines[input_line_idx] # a list of unique_id
        stations_mapping = {}

        for station in stations_on_line:
            for each in list_stations:
                if each['unique_id'] == station:
                    stations_mapping[each['human_name']] = station

        distance = {}
        for station in stations_mapping:
            distance[station] = math.sqrt(math.pow(stations[station]['x'] - stations[input_station]['x'], 2) +
                                        math.pow(stations[station]['y'] - stations[input_station]['y'], 2) +
                                        math.pow(stations[station]['z'] - stations[input_station]['z'], 2))
        
        sorted_station_d = sorted(distance.items(), key = lambda x:x[1])
        nearest_station = stations_mapping[sorted_station_d[0][0]] # unique id
        nearest_station_idx = stations_on_line.index(nearest_station)
        if nearest_station_idx == 0:
            return nearest_station_idx
        elif nearest_station_idx == len(stations_on_line) - 1:
            return nearest_station_idx + 1
        else:
            station_before = stations_on_line[nearest_station_idx - 1] # unique id
            station_after = stations_on_line[nearest_station_idx + 1] # unique id
            station_before_dist = distance[list(stations_mapping.keys())[list(stations_mapping.values()).index(station_before)]]
            station_after_dist = distance[list(stations_mapping.keys())[list(stations_mapping.values()).index(station_after)]]
            if station_before_dist < station_after_dist:
                return nearest_station_idx
            else:
                return nearest_station_idx + 1

    def goto_game(self, game_id: str):
        """
        go to a specific game
        """
        try:
            game_id_int = int(game_id.replace("Game", ""))
            #TODO look up to make sure this is a valid game...
            self.active_game = game_id_int
        except Exception as e:
            print("ERROR, trying to go to a game that doesn't exist: {}".format(game_id))
            pass

        print("ACTIVE GAME: {}".format(self.active_game))

    def create_line(self, station1: str, station2: str):
        """
        create a new line that connects station1 and station2
        """

        print("The current active game is Game {}".format(self.active_game))

        line_mapping, lines, stations = self.get_lines_and_stations()
        station1 = self.format_names(station1, stations)
        station2 = self.format_names(station2, stations)

        line_idx = None
        for line_color in line_mapping:
            line_uuid = line_mapping[line_color]
            if line_uuid not in lines or len(lines[line_uuid]) == 0:
                line_idx = self.line_names.index(line_color)
                break

        if line_idx is None:
            return False

        command1 = {
                'command': 'take_action',
                'game_id': self.active_game,
                'arguments': {
                    'action': "insert_station",
                    'line_index': line_idx,
                    'station_name': station1,
                    'insert_index': 0
                    }
                }
        result1 = self.send_and_recv(command1)
        print("Result of creating first station: ", result1)

        if result1["Status"] != "Success":
            return False

        command2 = {
                'command': 'take_action',
                'game_id': self.active_game,
                'arguments': {
                    'action': "insert_station",
                    'line_index': line_idx,
                    'station_name': station2,
                    'insert_index': 0
                    }
                }
        result2 = self.send_and_recv(command2)
        print("Result of creating second station: ", result2)

        if result2["Status"] != "Success":
            return False

        return True
    
    def alert_station(self, station):
        alert_msg = f"station {station} is timing out"
        print("WARNING " + alert_msg)
        alert_command = {"command":"speak", "response": alert_msg}
        result2 = self.send_and_recv(alert_command)
        if result2["Status"] != "Success":
            return False

        return True

    def delete_line(self, line):
        """
        delete the specified line
        """

        print("The current active game is Game {}".format(self.active_game))

        line = line.lower()

        line_mapping, lines, _ = self.get_lines_and_stations()
        line = self.format_names(line, line_mapping)
        line_idx = line_mapping[line]

        if line_idx not in lines or len(lines[line_idx]) == 0:
            return False

        command = {
                'command': 'take_action',
                'game_id': self.active_game,
                'arguments': {
                    'action': "remove_track",
                    'line_index': self.line_names.index(line)
                    }
                }
        result = self.send_and_recv(command)
        print("Result of deleting line: ", result)

        return result["Status"] == "Success"
    
    def wait_small(self):
        """
        waits for 1 seconds
        """
        sleep(1)
        return True
    
    def insert_station(self, station, line):
        """
        insert station to the given line
        """

        print("The current active game is Game {}".format(self.active_game))

        line = line.lower()
        line_mapping, lines, stations = self.get_lines_and_stations()
        line = self.format_names(line, line_mapping)
        line_idx = line_mapping[line]
        station = self.format_names(station, stations)

        if line_idx not in lines or len(lines[line_idx]) < 2:
            return False
        
        station_id = stations[station]['unique_id']
        if station_id in lines[line_idx]:
            return False
        
        insert_idx = self.find_nearest_station_sameline(station, line)
        # insert_idx = 0
        
        command = {
                    'command': 'take_action',
                    'game_id': self.active_game,
                    'arguments': {
                        'action': "insert_station",
                        'line_index': self.line_names.index(line),
                        'station_name': station,
                        'insert_index': insert_idx
                    }
        }
        result = self.send_and_recv(command)
        print("Result of inserting station: ", result)

        return result["Status"] == "Success"

    def remove_station(self, station, line):
        """
        remove the specified station from the given line
        """
        
        print("The current active game is Game {}".format(self.active_game))

        line = line.lower()

        line_mapping, lines, stations = self.get_lines_and_stations()
        line = self.format_names(line, line_mapping)
        line_idx = line_mapping[line]
        station = self.format_names(station, stations)

        if line_idx not in lines or len(lines[line_idx]) < 2:
            return False

        station_id = stations[station]['unique_id']
        if station_id not in lines[line_idx]:
            return False

        command = {
                'command': 'take_action',
                'game_id': self.active_game,
                'arguments': {
                    'action': "remove_station",
                    'line_index': self.line_names.index(line),
                    'station_name': station
                    }
                }
        result = self.send_and_recv(command)
        print("Result of removing station: ", result)

        return result["Status"] == "Success"
    
    def add_train(self, line):
        """
        add a new train from the given line
        """

        print("The current active game is Game {}".format(self.active_game))

        line = line.lower()
        line_mapping, lines, _ = self.get_lines_and_stations()
        line = self.format_names(line, line_mapping)
        line_idx = line_mapping[line]

        if line_idx not in lines or len(lines[line_idx]) == 0:
            return False

        command = {
                    'command': 'take_action',
                    'game_id': self.active_game,
                    'arguments': {
                        'action': "add_train",
                        'line_index': self.line_names.index(line)
                    }
            }
        result = self.send_and_recv(command)
        print("Result of adding a new train: ", result)

        return result["Status"] == "Success"
    
    def remove_train(self, line):
        """
        remove a train from the given line
        """
        
        print("The current active game is Game {}".format(self.active_game))

        line = line.lower()
        line_mapping, lines, _ = self.get_lines_and_stations()
        line = self.format_names(line, line_mapping)
        line_idx = line_mapping[line]

        if line_idx not in lines or len(lines[line_idx]) == 0:
            return False

        command = {
                    'command': 'take_action',
                    'game_id': self.active_game,
                    'arguments': {
                        'action': "remove_train",
                        'line_index': self.line_names.index(line)
                    }
            }
        result = self.send_and_recv(command)
        print("Result of adding a new train: ", result)

        return result["Status"] == "Success"
    
    def disconnect_random(self):
        _, lines, _ = self.get_lines_and_stations()
        return self.delete_line(random.choice(lines))


    def print_state_objects(self):
        line_mapping, lines, stations = self.get_lines_and_stations()
        station_mapping = {}
        for station_name in stations:
            station = stations[station_name]
            station_mapping[station['unique_id']] = station_name

        print("STATIONS:")
        for station_name in stations:
            print(station_name)

        print("LINES:")
        for line in lines:
            print("\t", line, "line:")
            for station_uuid in lines[line]:
                print("\t\t", station_mapping[station_uuid])
            print()