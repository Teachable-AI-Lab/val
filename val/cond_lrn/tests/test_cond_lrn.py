from val.cond_lrn.cond_lrn_stand import STAND, SkillApp

from cre import FactSet, Vectorizer, Flattener, define_fact
from copy import copy

def give_states_objs_types(state):
    new_state = []
    for d in state:
        _type = None
        if("object" in d):
            _type = d['object']
            if("dispenser" in _type or "pad" in _type):
                _type = "Object"
            if("pot" in _type):
                _type = "Pot"
        if("terrain" in d):
            _type = "Terrain"
        if(_type):
            _type = _type[0].upper() + _type[1:]
            new_state.append({"type" : _type ,**d})
    return new_state


_overcooked_state0 = [
 {'object': 'player', 'player_index': 0, 'x': 6, 'y': 2, 'orientation': 'down', 'is_me': 'False', 'holding': None},
 {'object': 'player', 'player_index': 1, 'x': 1, 'y': 1, 'orientation': 'left', 'is_me': 'True', 'holding': None},
 {'object': 'dish_dispenser', 'x': 3, 'y': 4},
 {'object': 'dish_dispenser', 'x': 5, 'y': 4},
 {'object': 'onion_dispenser', 'x': 0, 'y': 1},
 {'object': 'onion_dispenser', 'x': 5, 'y': 1},
 {'object': 'serving_pad', 'x': 3, 'y': 1},
 {'object': 'serving_pad', 'x': 8, 'y': 1},
 {'object': 'pot', 'x': 4, 'y': 2, 'status': 'empty', 'onion': 0, 'tomato': 0},
 {'object': 'pot', 'x': 4, 'y': 3, 'status': 'empty', 'onion': 0, 'tomato': 0},
 {'terrain': 'X', 'x': 0, 'y': 0},
 {'terrain': 'O', 'x': 0, 'y': 1},
 {'terrain': 'X', 'x': 0, 'y': 2},
 {'terrain': 'X', 'x': 0, 'y': 3},
 {'terrain': 'X', 'x': 0, 'y': 4},
 {'terrain': 'X', 'x': 1, 'y': 0},
 {'terrain': ' ', 'x': 1, 'y': 1},
 {'terrain': ' ', 'x': 1, 'y': 2},
 {'terrain': ' ', 'x': 1, 'y': 3},
 {'terrain': 'X', 'x': 1, 'y': 4},
 {'terrain': 'X', 'x': 2, 'y': 0},
 {'terrain': 'X', 'x': 2, 'y': 1},
 {'terrain': ' ', 'x': 2, 'y': 2},
 {'terrain': ' ', 'x': 2, 'y': 3},
 {'terrain': 'X', 'x': 2, 'y': 4},
 {'terrain': 'X', 'x': 3, 'y': 0},
 {'terrain': 'S', 'x': 3, 'y': 1},
 {'terrain': ' ', 'x': 3, 'y': 2},
 {'terrain': ' ', 'x': 3, 'y': 3},
 {'terrain': 'D', 'x': 3, 'y': 4},
 {'terrain': 'X', 'x': 4, 'y': 0},
 {'terrain': 'X', 'x': 4, 'y': 1},
 {'terrain': 'P', 'x': 4, 'y': 2},
 {'terrain': 'P', 'x': 4, 'y': 3},
 {'terrain': 'X', 'x': 4, 'y': 4},
 {'terrain': 'X', 'x': 5, 'y': 0},
 {'terrain': 'O', 'x': 5, 'y': 1},
 {'terrain': ' ', 'x': 5, 'y': 2},
 {'terrain': ' ', 'x': 5, 'y': 3},
 {'terrain': 'D', 'x': 5, 'y': 4},
 {'terrain': 'X', 'x': 6, 'y': 0},
 {'terrain': 'X', 'x': 6, 'y': 1},
 {'terrain': ' ', 'x': 6, 'y': 2},
 {'terrain': ' ', 'x': 6, 'y': 3},
 {'terrain': 'X', 'x': 6, 'y': 4},
 {'terrain': 'X', 'x': 7, 'y': 0},
 {'terrain': ' ', 'x': 7, 'y': 1},
 {'terrain': ' ', 'x': 7, 'y': 2},
 {'terrain': ' ', 'x': 7, 'y': 3},
 {'terrain': 'X', 'x': 7, 'y': 4},
 {'terrain': 'X', 'x': 8, 'y': 0},
 {'terrain': 'S', 'x': 8, 'y': 1},
 {'terrain': 'X', 'x': 8, 'y': 2},
 {'terrain': 'X', 'x': 8, 'y': 3},
 {'terrain': 'X', 'x': 8, 'y': 4},
 {'order': "('onion', 'onion', 'onion')", 'onion': 3, 'tomato': 0},
 {'timestep': 3}
]

overcooked_state0 = give_states_objs_types(_overcooked_state0)

_overcooked_state1 = copy(_overcooked_state0)
d = copy(_overcooked_state0[0])
d['holding'] = 'onion'
_overcooked_state1[0] = d
print(_overcooked_state1)
overcooked_state1 = give_states_objs_types(_overcooked_state1)


Player = define_fact("Player", {
        "object" : str,
        "player_index" : int,
        "x" : int,
        "y" : int,
        "orientation" : str,
        "is_me" : str, #TODO: should be bool?
        "holding": str
})

Pot  = define_fact("Pot", {
    "object" : str,
    "x" : int,
    "y" : int,
    'status': str, 
    'onion': int, 
    'tomato': int
})

Object = define_fact("Object", {
    "object" : str,
    "x" : int,
    "y" : int,
})

Terrain = define_fact("Terrain", {
    "terrain" : str,
    "x" : int,
    "y" : int,
})



vcr = Vectorizer()
flt = Flattener()
def to_vecs(state):

    fs = FactSet.from_py(state)
    # print(fs)
    flat_fs = flt.apply(fs)

    print(flat_fs)

    nom, cont = vcr.apply(flat_fs)
    return nom, cont

print("STATE0")
nom, _ = to_vecs(overcooked_state0)
print(nom)
print()
print("STATE1")
nom, _ = to_vecs(overcooked_state1)
print(nom)
print()
# print(nom, cont)


# overcooked_state1 = 

from shop2.domain import Method, Fact, Task, V
import faulthandler; faulthandler.enable()

# 1: on Methods
# 2: on Tasks
# 3: on callsite Task in a method

# A -> [a] (if not onion) | [epsilon] (if onion)

# G <- [(a*), b, c]
# G <- [e, d, f]

method = Method(
       head=('Cook', V("item")),
       preconditions=Fact(field=V('op'), operator='*'),
       subtasks=[Task('mult',)]
)
agent = object()

def new_cond_lrn_mech(method):
    return STAND(method, sanity_check=False)


skill_app0 = SkillApp(method, overcooked_state0, ("onion",))
skill_app1 = SkillApp(method, overcooked_state1, ("onion",))

mech = new_cond_lrn_mech(method)

mech.ifit(overcooked_state0, skill_app0, 1)
mech.ifit(overcooked_state1, skill_app1, -1)

lits_by_priority = mech.get_lit_priorities()
print(lits_by_priority)

# print("X_nom")
# print(mech.X_nom)
print(str(mech))

print(mech.get_conds())
print(mech.get_pyHTN_conds())


'''
Unary (type-definition given by object attr/vals): V(O) -> [O] is a [V]
    - character(Dwarf) -> Dwarf is a character
Binary (relation b/w objects): R(X, Y) -> [X] is [R] [Y]    
    - without types: above(w1, Human) -> w1 is above Human    
    - with types: above(w1, Human), character(Human), wall(w1) -> Wall w1 is above character Human
Binary (object attr/vals): A(O, V)    
    - numeric value: [O]'s [A] value is [V]    
    - categorical value: [O]'s [A] is [V]    
    - boolean value: [O] is [A] | [O] is not [A] 
    ''


A.mother == human -> A's mother is "human"
                  -> The thing mother A is "human"
                  -> The mother of A is human

A.above == human -> The above of A is "human
                 -> The thing above A is "human
                 -> A's above is "human"
                
'''
