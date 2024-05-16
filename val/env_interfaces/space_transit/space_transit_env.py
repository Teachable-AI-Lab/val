from typing import List
from typing import Tuple
import sys
import websocket
import importlib
import json

from nltk import edit_distance
from time import sleep
from pprint import pprint
from functools import partial

class SpaceTransitEnv():

    def __init__(self, url='ws://localhost:3000/metro'):
        self.url = url
        self.ws = websocket.create_connection(self.url)
        self.line_names = ["redline", "blueline", "yellowline"]

    def get_objects(self) -> List[str]:
        line_mapping, lines, stations = self.get_lines_and_stations()
        return list(stations.keys()) + list(line_mapping.keys())

    def get_actions(self) -> List[Tuple[str, List[str]]]:
        actions = []

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

        return actions

    def get_state(self) -> dict:
        """
        Returns the state in a dict that can be converted into HTN representation.
        """
        val_state = []
        cur_state = get_state_from_game()

        line_mapping = {}
        for line in cur_state['lines']:
            if line['id'] == 0:
                val_state.append({'line': 'redline', 'id': line['unique_id']})
            elif line['id'] == 1:
                val_state.append({'line': 'blueline', 'id': line['unique_id']})
            elif line['id'] == 2:
                val_state.append({'line': 'yellowline', 'id': line['unique_id']})

        for station in cur_state['stations']:
            val_state.append({'station': station['human_name'],
                              'unique_id': station['unique_id']})

        for segment in cur_state['segments']:
            if segment['which_line'] not in lines:
                val_state.append({'from_station': segment['from_station'],
                                  'to_station': segment['to_station'],
                                  'segment_line': segment['which_line']})

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
            if line['id'] == 0:
                line_mapping['redline'] = line['unique_id']
            elif line['id'] == 1:
                line_mapping['blueline'] = line['unique_id']
            elif line['id'] == 2:
                line_mapping['yellowline'] = line['unique_id']

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

    def create_line(self, station1: str, station2: str):
        line_mapping, lines, stations = get_lines_and_stations()

        station1 = format_names(station1, stations)
        station2 = format_names(station2, stations)

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
                'game_id': 0,
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
                'game_id': 0,
                'arguments': {
                    'action': "insert_station",
                    'line_index': line_idx,
                    'station_name': station2,
                    'insert_index': 0
                    }
                }
        result2 = send_and_recv(command2)
        print("Result of creating second station: ", result2)

        if result2["Status"] != "Success":
            return False

        update_val()

        return True

    def delete_line(self, line):
        line = line.lower()

        line_mapping, lines, _ = self.get_lines_and_stations()

        line = format_names(line, line_mapping)
        line_idx = line_mapping[line]

        if line_idx not in lines or len(lines[line_idx]) == 0:
            return False

        command = {
                'command': 'take_action',
                'game_id': 0,
                'arguments': {
                    'action': "remove_track",
                    'line_index': self.line_names.index(line)
                    }
                }
        result = self.send_and_recv(command)
        print("Result of deleting line: ", result)

        update_val()

        return result == "Success"

    def insert_station(self, line, station, station1, station2):
        """
        add specified station to the specified line
        between station1 and station2
        """
        line = line.lower()

        line_mapping, lines, stations = self.get_lines_and_stations()
        line = format_names(line, line_mapping)
        line_idx = line_mapping[line]

        station = format_names(station, stations)
        station1 = format_names(station1, stations)
        station2 = format_names(station2, stations)

        if line_idx not in lines or len(lines[line_idx]) < 2:
            return False

        station_id = stations[station]['unique_id']
        if station_id in lines[line_idx]:
            return False

        station1_id = stations[station1]['unique_id']
        if station1_id not in lines[line_idx]:
            return False

        station2_id = stations[station2]['unique_id']
        if station2_id not in lines[line_idx]:
            return False

        if abs(lines[line_idx].index(station1_id) -
               lines[line_idx].index(station2_id)) != 1:
            return False

        insert_idx = max(lines[line_idx].index(station1_id),
                         lines[line_idx].index(station2_id))

        command = {
                'command': 'take_action',
                'game_id': 0,
                'arguments': {
                    'action': "insert_station",
                    'line_index': self.line_names.index(line),
                    'station_name': station,
                    'insert_index': insert_idx
                    }
                }
        result = self.send_and_recv(command)
        print("Result of inserting station: ", result)

        update_val()

        return result == "Success"

    def append_station(self, line, station, end_station):
        """
        add specified station to the specified line
        between station1 and station2
        """
        line = line.lower()

        line_mapping, lines, stations = self.get_lines_and_stations()

        line = format_names(line, line_mapping)
        line_idx = line_mapping[line]

        station = format_names(station, stations)
        end_station = format_names(end_station, stations)

        if line_idx not in lines or len(lines[line_idx]) < 2:
            return False

        station_id = stations[station]['unique_id']
        if station_id in lines[line_idx]:
            return False

        end_station_id = stations[end_station]['unique_id']
        if end_station_id not in lines[line_idx]:
            return False

        station_idx = lines[line_idx].index(end_station_id)
        if station_idx != 0 and station_idx != len(lines[line_idx]):
            return False

        if station_idx == 0:
            insert_idx = 0
        else:
            insert_idx = len(lines[line_idx])

        command = {
                'command': 'take_action',
                'game_id': 0,
                'arguments': {
                    'action': "insert_station",
                    'line_index': self.line_names.index(line),
                    'station_name': station,
                    'insert_index': insert_idx
                    }
                }
        result = self.send_and_recv(json.dumps(command))
        print("Result of inserting station: ", result)

        update_val()

        return result == "Success"

    def remove_station(self, line, station):
        """
        add specified station to the specified line
        between station1 and station2
        """
        line = line.lower()

        line_mapping, lines, stations = self.get_lines_and_stations()
        line = format_names(line, line_mapping)
        line_idx = line_mapping[line]

        station = format_names(station, stations)

        if line_idx not in lines or len(lines[line_idx]) < 2:
            return False

        station_id = stations[station]['unique_id']
        if station_id not in lines[line_idx]:
            return False

        command = {
                'command': 'take_action',
                'game_id': 0,
                'arguments': {
                    'action': "remove_station",
                    'line_index': self.line_names.index(line),
                    'station_name': station
                    }
                }
        result = self.send_and_recv(json.dumps(command))
        print("Result of removing station: ", result)

        update_val()

        return result == "Success"

    def print_state_objects(self):
        line_mapping, lines, stations = get_lines_and_stations()
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



