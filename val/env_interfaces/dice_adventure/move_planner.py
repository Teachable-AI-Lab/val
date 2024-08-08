from py_search.base import Problem
from py_search.base import Node
from py_search.informed import best_first_search


class MovePlanner:
    def __init__(self):
        pass

    def get_next_move(self, src, dest, state, explore=False, visited=None):
        # print(f" SOURCE: {src} | DEST: {dest}")
        new_state = self._get_new_state(state, explore, visited)

        problem = DiceAdventureRouteProblem(src, goal=dest, extra=new_state)
        try:
            sol = next(best_first_search(problem))
            path = sol.path()
            cost = sol.cost()
            # print(path, sol.cost())
            if path:
                return path[0], cost
            else:
                return None, None

        except StopIteration:
            return None, None


    @staticmethod
    def _get_new_state(state, explore, visited):
        new_state = {
            "scene": state["content"]["scene"],
            "gameData": state["content"]["gameData"],
            "positions": {},
            "explore": explore,
            "visited": visited
        }
        for obj in new_state["scene"]:
            x, y = obj.get("x"), obj.get("y")
            if x is not None and y is not None:
                if (x, y) not in new_state["positions"]:
                    new_state["positions"][(x, y)] = [obj]
                else:
                    new_state["positions"][(x, y)].append(obj)
        # print(new_state["positions"])
        return new_state


class DiceAdventureRouteProblem(Problem):

    def successors(self, node):
        """
        Computes successors and computes the value of the node as cost.
        This will do something like breadth first.
        """
        # extra = self.base_env
        # print()
        curr_pos = node.state
        actions = [(1, 0), (-1, 0), (0, -1), (0, 1)]
        action_map = {(-1,0): "left", (1,0): "right", (0,1): "up", (0, -1): "down"}
        for action in actions:
            new_pos = (curr_pos[0] + action[0], curr_pos[1] + action[1])

            # Check if new position within bounds
            if new_pos[0] < 0 or new_pos[0] >= node.extra["gameData"]["boardWidth"] or \
                    new_pos[1] < 0 or new_pos[1] >= node.extra["gameData"]["boardHeight"]:
                pos = curr_pos
            # Check if new position has a wall
            elif new_pos in node.extra["positions"]:
                if any([str(obj.get("entityType")).lower() == "wall" for obj in node.extra["positions"][new_pos]]):
                    # print(f"***found wall at {new_pos}")
                    pos = curr_pos
                else:

                    pos = new_pos
            else:
                pos = new_pos

            # Get number of challenges at position
            total_cost = 1 + sum([10 if pos[0] == ele.get("x")
                                  and pos[1] == ele.get("y")
                                  and str(ele.get("entityType")).lower() in ["monster", "stone", "trap", "rock"] else 0
                                  for ele in node.extra["scene"]])
            if node.extra["explore"]:
                if pos in node.extra["visited"]:
                    total_cost += node.extra["visited"][pos]

            path_cost = node.cost() + total_cost
            yield Node(pos, node, action_map[action], path_cost, extra=node.extra)

    def goal_test(self, state_node, goal_node=None):
        if goal_node is None:
            goal = self.goal
        else:
            goal = goal_node.state
        # print(state_node.state)
        pos = state_node.state

        return pos[0] == goal[0] and pos[1] == goal[1]

