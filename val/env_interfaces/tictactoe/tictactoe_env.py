import platform
from subprocess import CREATE_NEW_CONSOLE
from subprocess import PIPE
from subprocess import Popen
from tabulate import tabulate
from val.src.val.env_interfaces.abstract_interface import AbstractEnvInterface
from val.src.val.env_interfaces.tictactoe.tictactoe import TicTacToe


class TicTacToeEnv(AbstractEnvInterface):

    def __init__(self):
        self.game = TicTacToe()
        # self.actions = [('place', ['s', 'x', 'y'])]
        self.actions = [
            {"name": "place",
             "args": ["?symbol", "?x", "?y"],
             "preconditions": [
                 {"type": "fact", "symbol": "?symbol", "x": "?x", "y": "?y"},
                 {"type": "filter", "lambda": f"x, y: 0 <= x < {self.game.size} and 0 <= y < {self.game.size}"},
                 {"type": "filter", "lambda": "symbol: symbol == ''"}
             ]}
        ]
        # self.terminal = self._create_terminal()

    def get_objects(self):
        objs = ["X", "O"]
        # objs = []
        # for x in range(self.game.size):
        #    for y in range(self.game.size):
        #        if self.game.board[x][y]:
        #            objs.append(f"{self.game.board[x][y]}{x}{y}")
        return objs

    def get_actions(self):
        """
        Returns actions in a format the HTN interface can create primitives.
        """

        return self.actions

    def get_state(self):
        """
        Returns the state in a dict that can be converted into HTN representation.
        """
        return [{"symbol": self.game.board[x][y], "x": x, "y": y}
                for x in range(self.game.size)
                for y in range(self.game.size)]

    def execute_action(self, action_name, args):
        """
        Takes an action and its arguments and executes it in the environment.
        """
        player, x, y = args
        """
        Fail in following 3 cases:
        1. Argument types are incorrect
        2. Board location already has a symbol
        3. There is already a winner
        4. x and y positions are not within bounds of board
        """
        # Fail if arguments are incorrect types or board location already has a symbol
        try:
            x = int(x)
            y = int(y)
            position = self.game.board[x][y]
        except ValueError:
            return False
        except IndexError:
            return False

        if position or self.game.check_winner() or (not self._in_bounds(x, y)):
            return False

        self.game.place(player, x, y)
        self._print_board(player, x, y)
        return True

    def _print_board(self, player, x, y):
        info = [
            ["Player:", player],
            ["Place:", f"({x},{y})"],
            ["Winner:", self._get_winner()]
        ]
        print(tabulate(info, tablefmt="grid"))
        self.game.print_board()

    def _get_winner(self):
        outcome = self.game.check_winner()
        if not outcome:
            outcome = None
        return outcome

    def _in_bounds(self, x, y):
        return 0 <= x < self.game.size and 0 <= y < self.game.size

    @staticmethod
    def _create_terminal():
        if platform.system() == "Windows":
            new_window_command = "cmd.exe /c start".split()
        else:  # XXX this can be made more portable
            new_window_command = "x-terminal-emulator -e".split()

        return Popen(new_window_command,
                     # shell=True,
                     stdout=PIPE,
                     stdin=PIPE,
                     creationflags=CREATE_NEW_CONSOLE)
