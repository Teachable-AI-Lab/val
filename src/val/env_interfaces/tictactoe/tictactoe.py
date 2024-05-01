from collections import Counter
from collections import defaultdict
from itertools import groupby
from json import dumps
from json import loads
from json.decoder import JSONDecodeError
from multiprocessing import Pool
from numpy import array_split
from numpy import transpose
from numpy import mean
from os import listdir
from os import mkdir
from os import makedirs
from os import path
from os import remove
from random import choice
from random import shuffle
from re import search
from threading import Thread
import time
# from concept_formation.cobweb import CobwebTree
# from concept_formation.multinomial_cobweb import MultinomialCobwebTree




WAIT_THRESHOLD = 30
WAIT_TIME = .1


class CommonData:
    """Represent an object that is shared between threads"""
    def __init__(self, player1, player2):
        self.player1 = player1
        self.player2 = player2
        self.actor = "driver"
        self.command = "play"
        self.game = TicTacToe(size=8, num_consecutive=5, player1=self.player1, player2=self.player2)
        self.terminate = False
        self.winner = None

    def reset(self):
        self.actor = "driver"
        self.command = "play"
        self.game = TicTacToe(size=8, num_consecutive=5, player1=self.player1, player2=self.player2)
        self.terminate = False
        self.winner = None


def main(num_games=1000, player1="X", player2="O"):
    start_time = time.time()
    # Used to swap between players when generating data
    player_swap = {player1: player2, player2: player1}

    common = CommonData(player1, player2)

    players = [
        Thread(target=load_player,
               args=(player, common))
        for player in player_swap
    ]
    for p in players:
        p.start()

    play_times = []
    win_counter = Counter()
    wins = []
    empty_spots = []
    final_states = []
    try:
        for i in range(num_games):
            play_start = time.time()
            print(f"Game ({i+1}/{num_games})")
            curr_player = player1
            common.actor = f"{curr_player}"

            while True:
                total_wait_time = 0
                while common.actor != "driver":
                    total_wait_time += WAIT_TIME
                    if total_wait_time >= WAIT_THRESHOLD:
                        exit(0)
                    time.sleep(WAIT_TIME)

                winner = common.game.check_winner()
                if not winner:
                    curr_player = player_swap[curr_player]
                    common.actor = f"{curr_player}"
                else:
                    print(f"WINNER: {winner}")
                    common.winner = winner
                    common.command = "train"
                    for p in player_swap:
                        common.actor = p
                        total_wait_time = 0
                        while common.actor != "driver":
                            total_wait_time += WAIT_TIME
                            if total_wait_time >= WAIT_THRESHOLD:
                                exit(0)
                            time.sleep(WAIT_TIME)
                    final_states.append(common.game.board)
                    break
            # Trackers
            winner_name = winner.split("-")[0]
            win_counter[winner_name] += 1
            wins.append(winner_name)
            empty_spots.append(len(common.game.get_empty_spots()))
            play_times.append(time.time()-play_start)
            # print(f"AVERAGE PLAY TIME FOR {i+1} ROUNDS: {round(mean(play_times), 2)} seconds")
            common.reset()
    except KeyboardInterrupt:
        common.actor = "terminate"
    # print(f"Total Time To Play {num_games} Games: {round((time.time()-start_time)/60, 2)} minutes")
    play_stats = {
        "Total Games": num_games,
        "Win Counts": win_counter,
        "Average Play Time": f"{round(mean(play_times), 2)} seconds",
        "Total Play Time": f"{round((time.time()-start_time)/60, 2)} minutes",
        "Play Times": play_times,
        "Winners": wins,
        "Empty Spots": empty_spots,
        "Final States": final_states
    }
    with open("game_stats.json", "w") as outfile:
        outfile.write(dumps(play_stats, indent=2))


def save_agent(agent, player_name):
    model = agent.dump_json()
    with open(f"{player_name}-model-2.json", "w") as outfile:
        outfile.write(model)


def load_player(player_name, common):
    agent = MultinomialCobwebTree()
    agent.load_json(open("reduced_ttt_agent.json").read())

    while True:
        total_wait_time = 0
        while common.actor != player_name:
            if common.actor == "terminate":
                exit(0)
            total_wait_time += WAIT_TIME
            if total_wait_time >= WAIT_THRESHOLD:
                print("WAIT TIME TOO LONG")
                save_agent(agent, player_name)
                exit(0)
            time.sleep(WAIT_TIME)

        if common.terminate:
            save_agent(agent, player_name)
            break

        command = common.command
        if command == "train":
            final_state = {k: {v: 1} for k, v in common.game.gameplay[-1].items() if v != ""}
            final_state["outcome"] = {common.winner: 1}
            agent.ifit(final_state)
            common.actor = "driver"
        elif command == "play":
            game = common.game
            empty_spots = game.get_empty_spots()
            choices = []
            state = {f"{x}-{y}": {game.board[x][y]: 1} for x in range(game.size) for y in range(game.size)
                     if game.board[x][y] != ""}
            for i, j in empty_spots:
                state[f"{i}-{j}"] = {player_name: 1}
                pred = agent.categorize(state).predict()
                choices.append((i, j, pred["outcome"][f"{player_name}-Wins"]))
                # Reset place on board
                state[f"{i}-{j}"] = {"": 1}
            best = sorted(choices, key=lambda x: x[2], reverse=True)[0]

            print(f"PLAYER: {player_name} | CHOICE: {best}")
            print(sorted(choices, key=lambda x: x[2], reverse=True))
            common.game.place(player_name, best[0], best[1])
            # Change actor to driver
            common.actor = "driver"



# DATA_DIR = "C:/Users/gsmith392/Documents/tic_tac_toe_data"


def count_states():
    import multiprocessing as mp
    import numpy as np

    data_dir = r"C:/Users/gsmith392/Documents/gomoku_data_reduced_2"
    files = [f"{data_dir}/{outcome_dir}/{file}" for outcome_dir in listdir(data_dir)
             for file in listdir(f"{data_dir}/{outcome_dir}")]

    pool = mp.Pool(12)
    jobs = np.array_split(files, 12)
    res = pool.map(count_states_mp, jobs)
    # res = pool.map(read_data2, jobs)
    c = {"Overall": {"state_count": 0, "game_count": 0, "states_by_game": Counter()},
         "B-Wins": {"state_count": 0, "game_count": 0, "states_by_game": Counter()},
         "W-Wins": {"state_count": 0, "game_count": 0, "states_by_game": Counter()},
         "Draw": {"state_count": 0, "game_count": 0, "states_by_game": Counter()}}
    for r in res:
        for outcome in r:
            c[outcome]["state_count"] += r[outcome]["state_count"]
            c[outcome]["game_count"] += r[outcome]["game_count"]
            c[outcome]["states_by_game"].update(r[outcome]["states_by_game"])

            c["Overall"]["state_count"] += r[outcome]["state_count"]
            c["Overall"]["game_count"] += r[outcome]["game_count"]
            c["Overall"]["states_by_game"].update(r[outcome]["states_by_game"])
    print(f"Final Counts: {c}")


def count_states_mp(files):
    c = {"B-Wins": {"state_count": 0, "game_count": 0, "states_by_game": Counter()},
         "W-Wins": {"state_count": 0, "game_count": 0, "states_by_game": Counter()},
         "Draw": {"state_count": 0, "game_count": 0, "states_by_game": Counter()}}
    for file in files:
        with open(file, "r") as infile:
            for line in infile:
                line = loads(line)

                outcome = list(line[0]["outcome"].keys())[0]
                c[outcome]["state_count"] += len(line)
                c[outcome]["game_count"] += 1
                c[outcome]["states_by_game"][len(line)] += 1
    print(c)
    return c


def read_data(files=None):
    data_dir = r"C:/Users/gsmith392/Documents/gomoku_data/reduced"
    files = [f"{data_dir}/{outcome_dir}/{file}" for outcome_dir in listdir(data_dir)
             for file in listdir(f"{data_dir}/{outcome_dir}")]
    total_files = len(files)
    all_games = defaultdict(list)

    for i, file in enumerate(files):
        with open(file, "r") as infile:
            print(file)
            print(f"File: ({i + 1}/{total_files})")
            # Only collect final states
            for line in infile:
                try:
                    game = loads(line)
                    # if counts[game[0]["outcome"]] >= 804150:
                    #    continue
                    all_games[game[0]["outcome"]].append([{k: {v: 1} for k, v in g.items()} for g in game])

                except JSONDecodeError:
                    continue
    return all_games


def reduce_data(num_workers=6):
    pool = Pool(num_workers)
    raw_data_dir = r"C:\Users\gsmith392\Documents\tic_tac_toe_data\old"
    new_data_dir = r"C:\Users\gsmith392\Documents\tic_tac_toe_data\new"

    files = [f"{raw_data_dir}/{outcome_dir}/{file}" for outcome_dir in listdir(raw_data_dir)
             for file in listdir(f"{raw_data_dir}/{outcome_dir}")]
    jobs = [[new_data_dir, file_partition] for file_partition in array_split(files, num_workers*2)]

    # pool.map(reduce_data_mp, jobs)
    for j in jobs:
        reduce_data_mp(j)


def reduce_data_mp(params):
    new_data_dir, files = params

    # data_dir = r"C:\Users\gsmith392\Documents\gomoku_data_reduced_2"

    for i, file in enumerate(files):
        games = []
        new_file = new_data_dir + "/" + "/".join(file.split("/")[-2:])

        with open(file, "r") as infile:
            # Only collect final states
            for line in infile:
                try:
                    game = loads(line)
                    # if counts[game[0]["outcome"]] >= 804150:
                    #    continue
                    games.append([{k: {v: 1} for k, v in g.items() if v != ""} for g in game])

                except JSONDecodeError:
                    continue
        with open(new_file, "w") as outfile:
            for g in games:
                outfile.write(f"{dumps(g)}\n")


# Total States To Categorize: Counter({'total_states': 103072020, 'W-Wins': 1123012, 'B-Wins': 804159, 'Draw': 140044})


    # return agent





# https://stackoverflow.com/questions/39922967/python-determine-tic-tac-toe-winner
class TicTacToe:
    def __init__(self, size=3, num_consecutive=3, player1="X", player2="O", save_as="dict"):
        self.size = size
        self.num_consecutive = num_consecutive
        self.board = [["" for _ in range(self.size)] for _ in range(self.size)]
        self.gameplay = []
        self.player1 = player1
        self.player2 = player2
        self.player_map = {self.player1: 1, self.player2: -1, "": 0}
        self.num_moves = 0
        self.max_moves = self.size * self.size
        self.save_as = save_as
        self.save_gameplay()

    def place(self, player, x, y):
        self.board[x][y] = player
        self.save_gameplay()
        self.num_moves += 1

    def save_gameplay(self):
        if self.save_as == "dict":
            temp = {f"{i}-{j}": self.board[i][j] for i in range(self.size) for j in range(self.size)}
        elif self.save_as == "num_matrix":
            temp = [self.player_map[self.board[i][j]] for i in range(self.size) for j in range(self.size)]
        self.gameplay.append(temp)

    def get_players(self):
        return [self.player1, self.player2]

    def get_empty_spots(self):
        return [(i, j) for i in range(self.size) for j in range(self.size) if self.board[i][j] == ""]

    def print_board(self):
        # use 3 below because there are 3 chars in the string ' | '
        for i in range(self.size):
            print(" | ".join(self.board[i]))
            print("_"*(self.size*3+self.size-2))

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
                        return f"{row_window[0]}-Wins"
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
                return f"{consecutive.group()[0]}-Wins"
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
                        return f"{g[0]}-Wins"

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
                    return f"{g[0]}-Wins"

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


if __name__ == "__main__":
    num_games = 1000
    player1 = "B"
    player2 = "W"
    main(num_games, player1, player2)
