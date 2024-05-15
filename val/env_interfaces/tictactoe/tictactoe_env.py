from tabulate import tabulate
from val.env_interfaces.abstract_interface import AbstractEnvInterface
from val.env_interfaces.tictactoe.tictactoe import TicTacToe


class TicTacToeEnv(AbstractEnvInterface):

    def __init__(self):
        self.reset()

    def reset(self):
        self.game = TicTacToe()

    def get_objects(self):
        return ["X", "O"] + [str(i) for i in range(self.game.size)]

    def get_actions(self):
        """
        Returns actions in a format the HTN interface can create primitives.
        """

        return [
            {"name": "place",
             "args": ["?symbol", "?x", "?y"],
             "preconditions": [
                 {"type": "fact", "mark": "?symbol", 'is-turn': "yes"},
                 {"type": "fact", "symbol": "", "x": "?x", "y": "?y"},
             ]},
            {"name": "reset",
             "args": [],
             "preconditions": []}
        ]

    def get_state(self):
        """
        Returns the state in a dict that can be converted into HTN representation.
        """
        state = [{"symbol": self.game.board[x][y], "x": x, "y": y}
                for x in range(self.game.size)
                for y in range(self.game.size)]

        num_x = [self.game.board[x][y]
                 for x in range(self.game.size)
                 for y in range(self.game.size)].count("X")

        if num_x % 2 == 0:
            state.append({'mark': 'X', "is-turn": "yes"})
            state.append({'mark': 'O', "is-turn": "no"})
        else:
            state.append({'mark': 'X', "is-turn": "no"})
            state.append({'mark': 'O', "is-turn": "yes"})

        return state

    def execute_action(self, action_name, args):
        """
        Takes an action and its arguments and executes it in the environment.
        """

        if action_name == "reset":
            self.reset()
            self.game.print_board()
            return True

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

        if position or self.game.check_winner():
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
