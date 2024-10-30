from typing import List
from typing import Tuple
import sys
import websocket
import random
import json
import math

from nltk import edit_distance
from time import sleep
from pprint import pprint
from functools import partial
from shop2.domain import Operator
from shop2.domain import Method
from shop2.domain import Task
from shop2.domain import Filter
from shop2.fact import Fact
from shop2.common import V


class SpaceTransitEnvHTN():

    def __init__(self, url='ws://localhost:3000/metro'):
        self.url = url
        self.ws = websocket.create_connection(self.url)
        self.line_names = ["redline", "blueline", "yellowline", "greenline", "purpleline"]
        self.active_game = 0

    def get_objects(self) -> List[str]:
        line_mapping, lines, stations = self.get_lines_and_stations()
        return list(stations.keys()) + list(line_mapping.keys())

    def get_actions(self) -> List[Tuple[str, List[str]]]:
        domain= {}
        descriptions = {}

        domain["create_line/2"] = [
            Operator(head=('create_line', V('station1'), V('station2')),
                     preconditions=Fact(station=V('station1')) & Fact(station=V('station2')),
                     effects=[]),
        ]
        descriptions["create_line/2"] = "create a new line that connects station1 and station2"

        domain["delete_line/1"] = [
            Operator(head=('delete_line', V('line1')),
                     preconditions=Fact(line=V('line1')),
                     effects=[]),
        ]
        descriptions["delete_line/1"] = "delete the specified line"

        domain["insert_station/2"] = [
            Operator(head=('insert_station', V('station'), V('line')),
                     preconditions=Fact(station=V('station')) & Fact(line=V('line')),
                     effects=[]),
        ]
        descriptions["insert_station/2"] = "insert station to the given line"

        domain["remove_station/2"] = [
            Operator(head=('remove_station', V('station'), V('line')),
                     preconditions=Fact(station=V('station')) & Fact(line=V('line')),
                     effects=[]),
        ]
        descriptions["remove_station/2"] = "remove the specified station from the given line"

        domain["goto_game/1"] = [
            Operator(head=('goto_game', V('game_id')),
                     preconditions=Fact(game=V('game_id')),
                     effects=[]),
        ]
        descriptions["goto_game/1"] = "go to a specific game with a given id"

        domain["add_train/1"] = [
            Operator(head=('add_train', V('line1')),
                     preconditions=Fact(line=V('line1')),
                     effects=[]),
        ]
        descriptions["add_train/1"] = "add train to the given line"

        domain["remove_train/1"] = [
            Operator(head=('remove_train', V('line1')),
                     preconditions=Fact(line=V('line1')),
                     effects=[]),
        ]
        descriptions["remove_train/1"] = "remove train to the given line"

        domain["connect_stations/0"] = [
            #no lines
            Method(head=('connect_stations',),
                   preconditions=Fact(station=V('station1'))&
                   Fact(station=V('station2'))&
                   Filter(lambda station1, station2: station1 != station2)&
                   Fact(any_lines=False),
                   subtasks=[Task('create_line', V('station1'), V('station2')), Task('connect_stations')]
                   ),
            Method(head=('connect_stations',),
                   preconditions=Fact(station=V('station1'))&
                   (~Fact(to_station=V('station1')) | ~Fact(from_station=V('station1')))&
                   Fact(station=V('station2'))&
                   Filter(lambda station1, station2: station1 != station2),
                   subtasks=[Task('create_line', V('station1'), V('station2')), Task('connect_stations')]
                   ),
        ]
        descriptions["connect_stations/0"] = "connect all unconnected stations"

        domain["remove_lines/0"] = [
            Method(head=('remove_lines',),
                   preconditions=Fact(line=V('line')),
                   subtasks=[Task('delete_line', V('line')), Task('remove_lines')]
                   )
        ]
        descriptions["remove_lines/0"] = "delete all the lines"

        

        return domain, descriptions
    
    def get_state(self) -> dict:
        """
        Returns the state in a dict that can be converted into HTN representation.
        """
        val_state = []
        cur_state = self.get_state_from_game()

        # line_mapping = {}
        any_lines = False
        for line in cur_state['lines']:
            any_lines = True
            val_state.append({'line': self.line_names[line['id']], 'id': line['unique_id']})

        for station in cur_state['stations']:
            val_state.append({'station': station['human_name'],
                              'unique_id': station['unique_id']})

        for segment in cur_state['segments']:
            if segment['which_line'] not in val_state: #TODO debug
                val_state.append({'from_station': segment['from_station'],
                                  'to_station': segment['to_station'],
                                  'segment_line': segment['which_line']})
        val_state.append({'any_lines': any_lines})

        return val_state

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

    def send_and_recv(self, message: dict):
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




