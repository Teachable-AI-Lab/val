from collections import defaultdict
from itertools import groupby
from numpy import transpose
from re import search
from tabulate import tabulate


class TicTacToe:
    def __init__(self, size=3, num_consecutive=3):
        self.size = size
        self.num_consecutive = num_consecutive
        self.board = [["" for _ in range(self.size)] for _ in range(self.size)]
        self.gameplay = []
        self.player1 = None
        self.player2 = None
        self.num_moves = 0
        self.max_moves = self.size * self.size
        self.save_gameplay()

    def place(self, player, x, y):
        if self.player1 and self.player2 and player not in self.get_players():
            raise ValueError(f"Symbol: {player} is not a valid option for this game.")
        # Set players
        if self.player1 is None:
            self.player1 = player
        elif self.player2 is None:
            self.player2 = player
        # Place symbol
        if 0 <= x < self.size and 0 <= y < self.size:
            self.board[x][y] = player
            self.save_gameplay()
            self.num_moves += 1
        else:
            raise ValueError("x or y position is out of bounds.")

    def save_gameplay(self):
        game_state = {f"{i}-{j}": self.board[i][j] for i in range(self.size) for j in range(self.size)}
        self.gameplay.append(game_state)

    def get_players(self):
        return [self.player1, self.player2]

    def get_empty_spots(self):
        return [(i, j) for i in range(self.size) for j in range(self.size) if self.board[i][j] == ""]

    def print_board(self):
        print(tabulate(self.board, tablefmt="grid"))

    def check_rows_columns2(self):
        for board in [self.board, transpose(self.board)]:
            for row in board:
                """
                if self.size == self.num_consecutive:
                    if len(set(row)) == 1 and row[0] != "":
                        return f"{row[0]}-Wins"
                else:
                """
                for i in range(self.size - self.num_consecutive + 1):
                    row_window = row[i:i+self.num_consecutive]
                    if len(set(row_window)) == 1 and row_window[0] != "":
                        return row_window[0]
        return False

    def check_diagonals2(self):
        diagonals = set()

        offset = 0
        while True:
            if offset + self.num_consecutive > self.size:
                break
            diags = defaultdict(list)
            for x in range(self.size - offset):
                diags["left"].append((x, x + offset))
                diags["left_flip"].append((x + offset, x))
                diags["right"].append((x, self.size - 1 - x - offset))
                diags["right_swap"].append((x + offset, self.size - 1 - x))
            for d in diags.values():
                diagonals.add(tuple(d))
            offset += 1

        for diag in diagonals:
            pieces = [self.board[d[0]][d[1]] for d in diag]
            pieces = [i if i else "#" for i in pieces]
            diag = "".join(pieces)
            consecutive = search(r'(.)'+self.num_consecutive*r"\1", diag)
            if consecutive and consecutive.group()[0] != "#":
                return consecutive.group()[0]
        else:
            return False

    def check_rows_columns(self):
        for board in [self.board, transpose(self.board)]:
            for row in board:
                """
                if self.size == self.num_consecutive:
                    if len(set(row)) == 1 and row[0] != "":
                        return f"{row[0]}-Wins"
                else:
                """
                groups = groupby(row)
                groups = sorted([(label, sum(1 for _ in group)) for label, group in groups],
                                key=lambda x: x[1],
                                reverse=True)
                for g in groups:
                    if g[0] == "":
                        continue
                    elif g[1] < self.num_consecutive:
                        break
                    else:
                        # if g[1] == self.num_consecutive:
                        return g[0]

        """
                for i in range(self.size - self.num_consecutive + 1):
                    row_window = row[i:i+self.num_consecutive]
                    if len(set(row_window)) == 1 and row_window[0] != "":
                        return f"{row_window[0]}-Wins"
        """
        return False

    def check_diagonals(self):
        diagonals = set()

        offset = 0
        while True:
            if offset + self.num_consecutive > self.size:
                break
            diags = defaultdict(list)
            for x in range(self.size - offset):
                diags["left"].append((x, x + offset))
                diags["left_flip"].append((x + offset, x))
                diags["right"].append((x, self.size - 1 - x - offset))
                diags["right_swap"].append((x + offset, self.size - 1 - x))
            for d in diags.values():
                diagonals.add(tuple(d))
            offset += 1

        for diag in diagonals:
            spots = [self.board[d[0]][d[1]] for d in diag]
            groups = groupby(spots)
            groups = sorted([(label, sum(1 for _ in group)) for label, group in groups],
                            key=lambda x: x[1],
                            reverse=True)
            for g in groups:
                if g[0] == "":
                    continue
                elif g[1] < self.num_consecutive:
                    break
                else:
                    # if g[1] == self.num_consecutive:
                    return g[0]

            return False

    def check_draw(self):
        """
        draw = all([self.board[i][j] for i in range(self.size) for j in range(self.size)])
        if draw:
            return "Draw"
        return False
        """
        return "Draw" if self.num_moves == self.max_moves else False

    def check_winner(self):
        # Transposition to check rows, then columns
        result = self.check_rows_columns()
        if result:
            return result
        result = self.check_diagonals()
        if result:
            return result
        return self.check_draw()
