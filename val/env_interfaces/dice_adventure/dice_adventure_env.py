import copy
from json import loads
from typing import List
from typing import Tuple
from val.env_interfaces.abstract_interface import AbstractEnvInterface
from val.env_interfaces.dice_adventure.game.dice_adventure_python_env import DiceAdventurePythonEnv
from val.env_interfaces.dice_adventure.move_planner import MovePlanner

import os
import json

from pyhtn.htn import Task, Method, Operator, TaskEx, MethodEx, OperatorEx
from pyhtn.conditions.fact import Fact
from pyhtn.conditions.conditions import NOT
from pyhtn.domain.variable import V
from pyhtn.conditions.pattern_matching import Filter

class DiceAdventureEnv(AbstractEnvInterface):

    def __init__(self, player="Dwarf", server="unity", state_version="fow"):
        self.player = player
        self.character_id = "C11"
        self.env = DiceAdventurePythonEnv(player=player, server=server, state_version=state_version)
        self.env.register(self.player)
        self.move_planner = MovePlanner()

    def get_objects(self) -> List[str]:
        state = self.env.get_state()
        char_map = {"C11": "Dwarf", "C21": "Giant", "C31": "Human"}
        objects = [f'{ele["entityType"]}-{ele["id"]}' for ele in state["content"]["scene"]]
        for id_, char in char_map.items():
            for i in range(len(objects)):
                if objects[i].split("-")[1] == id_:
                    objects[i] = f"{char}-{id_}"
                    break
        return objects

    def get_actions(self) -> List[Tuple[str, List[str]]]:
        domain = {}
        descriptions = {}

        domain["up"] = [
            Operator(
                name="up",
                args=(),
                preconditions=[],
                effects=[]
            )
        ]
        descriptions["up"] = "Increases the player's y position by one unit."

        domain["down"] = [
            Operator(
                name="down",
                args=(),
                preconditions=[],
                effects=[]
            )
        ]
        descriptions["down"] = "Decreases the player's y position by one unit."

        domain["left"] = [
            Operator(
                name="left",
                args=(),
                preconditions=[],
                effects=[]
            )
        ]
        descriptions["left"] = "Decreases the player's x position by one unit."

        domain["right"] = [
            Operator(
                name="right",
                args=(),
                preconditions=[],
                effects=[]
            )
        ]
        descriptions["right"] = "Increases the player's x position by one unit."

        domain["wait"] = [
            Operator(
                name="wait",
                args=(),
                preconditions=[],
                effects=[]
            )
        ]
        descriptions["wait"] = "Keeps the player's x and y position the same."

        domain["move_to"] = [
            Operator(
                name="move_to",
                args=(V("target"),),
                preconditions=[
                    # Fact("currentPhase", "Player_Planning"),
                    # Fact("actionPoints", V("ap")),
                    # Filter(lambda ap: ap > 0)
                ],
                effects=[]
            ),
            # Operator(
            #     name="move_to",
            #     args=(V("direction"), V("num_steps")),
            #     preconditions=[
            #         Fact("currentPhase", "Player_Planning"),
            #         Fact("actionPoints", V("ap")),
            #         Filter(lambda ap: ap > 0)
            #     ],
            #     effects=[]
            # ),
            # Operator(
            #     name="move_to",
            #     args=(V("target"), V("direction"), V("num_steps")),
            #     preconditions=[
            #         Fact("currentPhase", "Player_Planning"),
            #         Fact("actionPoints", V("ap")),
            #         Filter(lambda ap: ap > 0)
            #     ],
            #     effects=[]
            # )
        ]
        descriptions["move_to"] = "Only have one args, which is the targeted location. Move to the target location."

        domain["submit"] = [
            Operator(
                name="submit",
                args=(),
                preconditions=[],
                effects=[]
            )
        ]
        descriptions["submit"] = "Submits the final action or plan."

        for pin_type in ['pinga', 'pingb', 'pingc', 'pingd']:
            domain[pin_type] = [
                Operator(
                    name=pin_type,
                    args=(),
                    preconditions=[
                        Fact("actionPoints", V("ap")),
                        Filter(lambda ap: ap > 0)
                    ],
                    effects=[]
                )
            ]
        descriptions[pin_type] = f"Places a type '{pin_type[-1].upper()}' pin on the game board."
        
        domain["find_tower"] = [
            Method(
                name="find_tower",
                args=(),
                preconditions=[],
                subtasks=[Task("explore"), 
                          Task("find_tower")]
            ),
            Method(
                name="find_tower",
                args=(),
                preconditions=[
                    Fact(entityType="Goal", x=V("gx"), y=V("gy")),
                ],
                subtasks=[Task("move", V("gx"), V("gy")), 
                          Task("find_tower")]
            ),]
        descriptions["find_tower"] = "Searches for a tower after shrine is reached. Moves, explores, or submits when out of points."
        
        domain["explore"] = [
            Method(
                name="explore",
                args=(),
                preconditions=[
                    # Fact(id="gameData", currentPhase="Player_Planning"),
                    Fact(sight_status="unexplored", x=V("gx"), y=V("gy"))
                ],
                subtasks=[Task("move", V("gx"), V("gy"))]
            )
        ]
        descriptions["explore"] = "Moves the player to an unexplored location based on current position."
        
        domain["move"] = [
            Operator(
                name="move",
                args=(V("dest_x"), V("dest_y")),
                preconditions=[],
                effects=[
                    Fact(type="action", value="move")
                ]
            )
        ]
        
        descriptions["move"] = "Moves the player from one location to another."
        
        domain["play"] = [
            Method(
                name="play",
                args=(),
                preconditions=[],
                subtasks=[Task("explore"), Task("find_shrine"), Task("find_tower")]
            )
        ]
        descriptions["play"] = "Controls the main game loop across phases: pinning, planning, and infinite continuation."

        domain["find_shrine"] = [
            Method(
                name="find_shrine",
                args=(),
                preconditions=[
                    # game environment name bug
                    Fact(entityType="Shrine", objKey='K1', reached=False, x=V("sx"), y=V("sy")), 
                    Fact(entityType="Character", objKey=self.character_id, actionPoints=V("ap")),
                    Filter(lambda ap: ap > 0)
                ],
                subtasks=[Task("move", V("sx"), V("sy"))]
            ),
          
            Method(
                name="find_shrine",
                args=(),
                preconditions=[],
                subtasks=[Task("explore"),Task("find_shrine")]
            ),
            
            Method(
                name="find_shrine",
                args=(),
                preconditions=[],
                subtasks=[Task("submit")]
            )
        ]
        descriptions["find_shrine"] = "Searches for a shrine by moving, exploring, or submitting if reached or out of action points."

        # domain["find_tower"] = [
        #     Method(
        #         name="find_tower",
        #         args=(),
        #         preconditions=[
        #             Fact(id="gameData", currentPhase="Player_Planning"),
        #             Fact(entityType="Shrine", character=self.character_id, reached=True),
        #             Fact(entityType="Goal", x=V("gx"), y=V("gy")),
        #             Fact(entityType="Character", id=self.character_id, x=V("px"), y=V("py"), actionPoints=V("ap")),
        #             Filter(lambda ap: ap > 0)
        #         ],
        #         subtasks=[Task("move", V("px"), V("py"), V("gx"), V("gy")), 
        #                   Task("find_tower")]
        #     ),
            # Method(
            #     name="find_tower",
            #     args=(),
            #     preconditions=[
            #         Fact(id="gameData", currentPhase="Player_Planning"),
            #         Fact(entityType="Shrine", character=self.character_id, reached=True),
            #         Fact(entityType="Character", id=self.character_id, x=V("px"), y=V("py"), actionPoints=V("ap")),
            #         Filter(lambda ap: ap > 0)
            #     ],
            #     subtasks=[Task("explore", V("px"), V("py")), 
            #               Task("find_tower")]
            # ),
        #     Method(
        #         name="find_tower",
        #         args=(),
        #         preconditions=[
        #             Fact(id="gameData", currentPhase="Player_Planning"),
        #             Fact(entityType="Character", id=self.character_id, x=V("px"), y=V("py"), actionPoints=V("ap")),
        #             Filter(lambda ap: ap <= 0)
        #         ],
        #         subtasks=[Task("submit")]
        #     )
        # ]
        # descriptions["find_tower"] = "Searches for a tower after shrine is reached. Moves, explores, or submits when out of points."



        return domain, descriptions

    def get_state(self) -> list:
        """
        Returns the simplified game state with sight_status and unexplored cells,
        formatted for HTN use.
        """
        state = self.env.get_state()
        simplified_scene = _simplify_state(state, self.player)

        # Convert list-type values to string for HTN compatibility
        for obj in simplified_scene:
            for k, v in obj.items():
                if isinstance(v, list):
                    obj[k] = ",".join(map(str, v))

        print("state:", simplified_scene)
        return simplified_scene
    
    
    def execute_action(self, action_name: str, args: List[str]) -> bool:
        """
        Takes an action and its arguments and executes it in the environment.
        """
        state = self.env.get_state()
        player_obj = self.find_obj_by_id(state, self.env.get_player_code(self.player) + "1")
        if action_name == "move_to":
            target_pos = self.get_target_pos(args[0], state)
            print("target_pos:", target_pos)
            self.move_to_target(target_pos, player_obj, state)
            # if len(args) == 1:
            #     target_pos = self.get_target_pos(args[0], state)
            #     self.move_to_target(target_pos, player_obj, state)
            # elif len(args) == 2:
            #     self.move_in_direction(args[0], int(args[1]), player_obj, state)
            # elif len(args) == 3:
            #     target_pos = self.get_target_pos(args[0], state)
            #     tx, ty = self.change_position(target_pos, args[1], int(args[2]))
            #     self.move_to_target((tx, ty), player_obj, state)
            return True
        if action_name == "move":
            target_pos = (args[0], args[1])
            self.move_to_target(target_pos, player_obj, state)
        else:
            next_state = self.env.execute_action(player=self.player, game_action=action_name)
            self.env.render()
            return next_state["status"] != "ILLEGAL_ACTION"

    def move_in_direction(self, direction, num_steps, player_obj, state):
        target_x, target_y = self.change_position((player_obj["x"], player_obj["y"]), direction, num_steps)
        self.move_to_target((target_x, target_y), player_obj, state)

    @staticmethod
    def change_position(pos, direction, num_steps):
        x, y = pos
        if direction == "left":
            x -= num_steps
        elif direction == "right":
            x += num_steps
        elif direction == "up":
            y += num_steps
        elif direction == "down":
            y -= num_steps
        return x, y

    def move_to_target(self, target_pos, player_obj, state):
        while player_obj["actionPoints"] > 0:
            px, py = self.get_x_y_cursor(player_obj["x"], player_obj["y"], player_obj["actionPlan"])
            action = self.get_next_move_action((px, py), target_pos, state)
            if action is None:
                break
            state = self.env.execute_action(player=self.player, game_action=action)
            player_obj = self.find_obj_by_id(state, self.env.get_player_code(self.player) + "1")
        self.env.execute_action(player=self.player, game_action="submit")

    def get_target_pos(self, target, state):
        target_id = target.split("-")[-1].strip()
        # Convert character names to Ids if needed
        if target_id in self.env.get_player_names():
            target_id = self.env.get_player_code(target_id) + "1"
        target_obj = self.find_obj_by_id(state, target_id)
        return target_obj["x"], target_obj["y"]

    @staticmethod
    def get_x_y_cursor(x, y, action_plan):
        for action in action_plan:
            action = action.lower()
            if action == "up":
                y += 1
            elif action == "down":
                y -= 1
            elif action == "left":
                x -= 1
            elif action == "right":
                x += 1
            elif action == "wait":
                pass
        return x, y

    def get_next_move_action(self, src, dest, state):
        return self.move_planner.get_next_move(src, dest, state)[0]

    @staticmethod
    def find_obj_by_id(state, obj_id):
        for obj in state["content"]["scene"]:
            if obj.get("id") == obj_id:
                return obj


#############
# UTILITIES #
#############
def _simplify_state(state: dict, player: str) -> list[dict]:
    """
    Simplifies the game state into a list of dictionary objects, each representing an object in the game.
    :param state: The game state
    :param player: The player the state is related to
    :return: The modified state as a list of dictionaries
    """
    state['content']['gameData']['id'] = 'gameData'
    game_data_obj = state['content']['gameData']
    scene = [game_data_obj] + state['content']['scene']

    return _add_sight_status(scene, player, game_data_obj)


def _add_sight_status(scene: list[dict], player: str, game_data_obj: dict) -> list[dict]:
    """
    Modifies the state by adding whether objects are visible or hidden. It also adds 'Cell' objects with an 'unexplored'
    status to represent grid squares that have not yet been observed.
    :param scene: The list of objects in the state
    :param player: The name of the player
    :param game_data_obj: The state object containing high level information about the current state of the game
    :return: The modified scene list
    """
    player_obj = _find_player_obj(scene, player)
    x_lower = player_obj['x'] - player_obj['sightRange']
    x_upper = player_obj['x'] + player_obj['sightRange']
    y_lower = player_obj['y'] - player_obj['sightRange']
    y_upper = player_obj['y'] + player_obj['sightRange']

    all_cells = {(i, j) for i in range(game_data_obj['boardWidth']) for j in range(game_data_obj['boardHeight'])}
    scene_cells = {(obj.get('x'), obj.get('y')) for obj in scene}
    unexplored = all_cells - scene_cells

    for obj in scene:
        x, y = obj.get('x'), obj.get('y')
        if x is None or y is None:
            continue
        if x_lower <= x <= x_upper and y_lower <= y <= y_upper:
            obj['sight_status'] = 'visible'
        else:
            obj['sight_status'] = 'hidden'

    for i, pos in enumerate(unexplored):
        scene.append({'id': f'UE{i}', 'entityType': 'Cell',
                      'objKey': 'UE', 'sight_status': 'unexplored',
                      'x': pos[0], 'y': pos[1]})
    return scene


def _find_player_obj(scene: list[dict], player: str) -> dict | None:
    """
    Locates the player's object dictionary in the scene list.
    :param scene: The list of objects in the state
    :param player: The name of the player to be returned
    :return: The player dictionary object
    """
    ids = {"dwarf": "C11", "giant": "C21", "human": "C31"}
    pid = ids[player.lower()]
    for obj in scene:
        if obj.get('id') == pid:
            return copy.copy(obj)


if __name__ == "__main__":
    env = DiceAdventureEnv()
    env.execute_action(action_name="find_shrine", args=[])

