from random import randint
from random import choice
from val.src.val.env_interfaces.abstract_interface import AbstractEnvInterface


class FractionArithmeticTutorEnv(AbstractEnvInterface):

    def __init__(self, lower_bound=1, upper_bound=10):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.problem = self._get_problem()
        self.actions = [('input_value', ['value', 'field']), ('click_done', [])]

    def get_objects(self):
        return list(self.problem.keys())

    def get_actions(self):
        """
        Returns actions in a format the HTN interface can create primitives.
        """
        return self.actions

    def get_state(self) -> dict:
        """
        Returns the state in a dict that can be converted into HTN representation.
        """
        return {"state": [{"field": k, "value": v}
                          for k, v in self.problem.items()]}

    def execute_action(self, action_name, args):
        """
        Takes an action and its arguments and executes it in the environment.
        """

        if action_name == "input_value":
            field, value = args
            self.problem[field] = value
        elif action_name == "click_done":
            self.problem["done"] = True
        else:
            return False

        return True

    def _get_problem(self):
        return {
            "left_numerator": randint(self.lower_bound, self.upper_bound),
            "left_denominator": randint(self.lower_bound, self.upper_bound),
            "right_numerator": randint(self.lower_bound, self.upper_bound),
            "right_denominator": randint(self.lower_bound, self.upper_bound),
            "operator": choice(["+", "*"]),
            "answer_numerator": None,
            "answer_denominator": None,
            "check_convert": None,
            "left_numerator_convert": None,
            "left_denominator_convert": None,
            "right_numerator_convert": None,
            "right_denominator_convert": None,
            "done": False
        }
