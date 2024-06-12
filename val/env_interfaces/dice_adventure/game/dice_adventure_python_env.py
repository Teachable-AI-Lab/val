from val.env_interfaces.dice_adventure.game.dice_adventure import DiceAdventure
import val.env_interfaces.dice_adventure.game.unity_socket as unity_socket
from gymnasium import Env
from json import loads


class DiceAdventurePythonEnv(Env):
    """
    Implements a custom gyn environment for the Dice Adventure game.
    """
    def __init__(self,
                 player="Dwarf",
                 id_=0,
                 train_mode=False,
                 server="local",
                 state_version="player",
                 **kwargs):
        """
        Init function for Dice Adventure gym environment.
        :param player:      (string) The player that will be used to play the game.
        :param id_:         (int) An optional ID parameter to distinguish this environment from others.
        :param train_mode:  (bool) A helper parameter to switch between training mode and play mode. When we test agents,
                                   we will use a "play" mode, where the step function simply takes an action and returns
                                   the next state.
        :param server:      (string) Determines which game version to use. Can be one of {local, unity}.
        :param kwargs:      (dict) Additional keyword arguments to pass into Dice Adventure game. Only applies when
                                   'server' is 'local'.
        """
        self.config = loads(open("game/config/main_config.json", "r").read())
        self.player = player
        self.id = id_
        self.kwargs = kwargs
        self.actions = ["up", "down", "left", "right", "wait", "undo", "submit", "pinga", "pingb", "pingc", "pingd"]
        self.player_names = ["Dwarf", "Giant", "Human"]

        ##################
        # STATE SETTINGS #
        ##################
        self.state_version = state_version if state_version in ["full", "player", "fow"] else "player"

        ##################
        # TRAIN SETTINGS #
        ##################
        self.train_mode = train_mode

        ###################
        # SERVER SETTINGS #
        ###################
        self.server = server
        self.unity_socket_url = self.config["GYM_ENVIRONMENT"]["UNITY"]["URL"]
        self.game = DiceAdventure(**self.kwargs) if self.server == "local" else None

    def step(self, action):
        """
        Applies the given action to the game.
        If self.train_mode == True, passes action to _step_train() and returns new information for RL model.
        If self.train_mode == False, simply returns state obtained after taking action.
        :param action:  (string) The action produced by the agent
        :return:        (dict, float, bool, bool, dict) or (dict)
        """
        if self.train_mode:
            return self._step_train(action)
        else:
            return self._step_play(action)

    def _step_train(self, action):
        """
        Applies the given action to the game. Determines the next observation and reward,
        whether the training should terminate, whether training should be truncated, and
        additional info.
        :param action:  (string) The action produced by the agent
        :return:        (dict, float, bool, bool, dict) See below

        new_obs (dict) - The resulting game state after applying 'action' to the game
        reward (float) - The reward obtained from applying 'action' to the game. This must be defined by the user. A
                         helper function _get_reward() has been provided for convenience.
        terminated (bool) - Whether the game has terminated after applying 'action' to the game
        truncated (bool) - (See https://farama.org/Gymnasium-Terminated-Truncated-Step-API)
        info (dict) - Additional information that should be passed back to model

        Note: Although this framework is usually used for RL models, users can develop any kind of model with this code.
        """
        next_state = self.execute_action(self.player, action)

        reward = self._get_reward()

        # new_obs, reward, terminated, truncated, info
        terminated = next_state["status"] == "Done"
        if terminated:
            new_obs, info = self.reset()
        else:
            new_obs, info = self.get_state(), {}
        truncated = False

        return new_obs, reward, terminated, truncated, info

    def _step_play(self, action):
        """
        Applies the given action to the game and returns the resulting state
        :param action:  (string) The action produced by the agent
        :return:        (dict) The resulting state
        """
        return self.execute_action(self.player, action)

    def close(self):
        """
        close() function from standard gym environment. Not implemented.
        :return: N/A
        """
        pass

    def render(self, mode='console'):
        """
        Prints the current board state of the game. Only applies when `self.server` is 'local'.
        :param mode: (string) Determines the mode to use (not used)
        :return: N/A
        """
        if self.server == "local":
            self.game.render()

    def reset(self, **kwargs):
        """
        Resets the game. Only applies when `self.server` is 'local'.
        :param kwargs:  (dict) Additional arguments to pass into local game server
        :return:        (dict, dict) The initial state when the game is reset, An empty 'info' dict
        """
        if self.server == "local":
            self.game = DiceAdventure(**self.kwargs)
        obs = self.get_state()
        return obs, {}

    def execute_action(self, player, game_action):
        """
        Executes the given action for the given player.
        :param player:      (string) The player that should take the action
        :param game_action: (string) The action to take
        :return:            (dict) The resulting state after taking the given action
        """
        if self.server == "local":
            self.game.execute_action(player, game_action)
            next_state = self.get_state()
        else:
            url = self.unity_socket_url.format(player.lower())
            # TODO CAPTURE RESPONSE AND RETURN TO USER
            unity_socket.execute_action(url, game_action)
            next_state = self.get_state()
        return next_state

    def get_state(self, player=None, version=None, server=None):
        """
        Gets the current state of the game.
        :param player: (string) The player whose perspective will be used to collect the state. Can be one of
                                {Dwarf, Giant, Human}.
        :param version: (string) The level of visibility. Can be one of {full, player, fow}
        :param server: (string) Determines whether to get state from Python version or Unity version of game. Can be
                                one of {local, unity}.
        :return: (dict) The state of the game

        The state is always given from the perspective of a player and defines how much of the level the
        player can currently "see". The following state version options define how much information this function
        returns.
        - [full]:   Returns all objects and player stats for current level. This ignores the 'player' parameter.

        - [player]: Returns all objects in the current sight range of the player. Limited information is provided about
                    other players present in the state.

        - [fow]:    Stands for Fog of War. In the Unity version of the game, you can see a visibility mask for each
                    character. Black positions have not been observed. Gray positions have been observed but are not
                    currently in the player's view. This option returns all objects in the current sight range (view) of
                    the player plus objects in positions that the player has seen before. Note that any object that can
                    move (such as monsters and other players) are only returned when they are in the player's current
                    view, but static objects such as walls, stones, and traps are returned if they've been previously
                    observed.
        """
        version = version if version is not None else self.state_version
        player = player if player is not None else self.player
        server = server if server else self.server

        if server == "local":
            state = self.game.get_state(player, version)
        else:
            url = self.unity_socket_url.format(player.lower())
            state = unity_socket.get_state(url, version)

        return state

    def get_actions(self):
        return self.actions

    def get_player_names(self):
        return self.player_names

    @staticmethod
    def get_player_code(player):
        codes = {"Dwarf": "C1", "Giant": "C2", "Human": "C3"}
        return codes[player]

    @staticmethod
    def _get_reward():
        """
        Calculates the reward the agent should receive based on action taken.
        :return: (int) The reward
        """
        return 0
