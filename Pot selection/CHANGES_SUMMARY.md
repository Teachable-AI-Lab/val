# Changes Summary: Simple vs Enhanced Pot Selection

## 🔄 Quick Comparison

| Feature | Simple Version (Current) | Enhanced Version (Pot Selection) |
|---------|-------------------------|----------------------------------|
| **Pot Naming** | Generic "pot" | Distinct "pot1" and "pot2" |
| **Player Holding Check** | ❌ No | ✅ Yes |
| **Preconditions** | ❌ None | ✅ Extensive |
| **Boil Methods** | 3 generic | 9 specific |
| **Plate Methods** | ❌ Commented out | 7 specific |
| **Routing** | Generic | Position-based |
| **State Facts** | Basic | Enhanced with player_holding |

## 📝 Detailed Changes

### 1. Import Changes

**Added:**
```python
# No new imports needed - all functionality uses existing libraries
```

### 2. HTN Method Changes

#### A. Cook Method
**Before:**
```python
domain["cook"] = [
    Method(
        name='cook',
        args=(V('object'),),
        preconditions=[],
        subtasks=[
            Task('get', V('object')),
            Task('boil',V('object')),
            Task('plate'),
            Task('deliver')
        ]
    ),
]
```

**After:**
```python
domain["cook"] = [
    Method(
        name='cook',
        args=(V('object'),),
        preconditions=[],
        subtasks=[
            Task('get', V('object')),
            Task('boil',V('object')),
            Task('get', 'dish'),  # ADDED: Explicit get dish
            Task('plate'),
            Task('deliver')
        ]
    ),
]
```

#### B. Boil Method
**Before (3 methods, no preconditions):**
```python
domain["boil"] = [
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[],
        subtasks=[
            Task('go to', 'pot'),
            Task('interact')
        ]
    ),
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[],
        subtasks=[
            Task('interact')
        ]
    ),
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[],
        subtasks=[
            Task('go to', 'pot'),
            Task('interact'),
            Task('interact'),
            Task('wait 20min')  # NOTE: Wait was removed in final version
        ]
    )
]
```

**After (9 methods with specific preconditions):**
```python
domain["boil"] = [
    # Method 1: Already holding object, use empty pot1
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[
            Fact(player_holding=V('object')),
            Fact(id='pot1', object='pot1', status='empty')
        ],
        subtasks=[
            Task('go to', 'pot1'),
            Task('interact')
        ]
    ),
    # Method 2: Already holding object, use empty pot2
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[
            Fact(player_holding=V('object')),
            Fact(id='pot2', object='pot2', status='empty')
        ],
        subtasks=[
            Task('go to', 'pot2'),
            Task('interact')
        ]
    ),
    # Method 3: Already holding object, add to pot1 with 1 item
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[
            Fact(player_holding=V('object')),
            Fact(id='pot1', object='pot1', status='1_items')
        ],
        subtasks=[
            Task('go to', 'pot1'),
            Task('interact')
        ]
    ),
    # Method 4: Already holding object, add to pot2 with 1 item
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[
            Fact(player_holding=V('object')),
            Fact(id='pot2', object='pot2', status='1_items')
        ],
        subtasks=[
            Task('go to', 'pot2'),
            Task('interact')
        ]
    ),
    # Method 5: Don't have object, get it first, then use empty pot1
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[
            NOT(Fact(player_holding=V('object'))),
            Fact(id='pot1', object='pot1', status='empty')
        ],
        subtasks=[
            Task('get', V('object')),
            Task('go to', 'pot1'),
            Task('interact')
        ]
    ),
    # Method 6: Don't have object, get it first, then use empty pot2
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[
            NOT(Fact(player_holding=V('object'))),
            Fact(id='pot2', object='pot2', status='empty')
        ],
        subtasks=[
            Task('get', V('object')),
            Task('go to', 'pot2'),
            Task('interact')
        ]
    ),
    # Method 7: Don't have object, get it, add to pot1 with 1 item
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[
            NOT(Fact(player_holding=V('object'))),
            Fact(id='pot1', object='pot1', status='1_items')
        ],
        subtasks=[
            Task('get', V('object')),
            Task('go to', 'pot1'),
            Task('interact')
        ]
    ),
    # Method 8: Don't have object, get it, add to pot2 with 1 item
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[
            NOT(Fact(player_holding=V('object'))),
            Fact(id='pot2', object='pot2', status='1_items')
        ],
        subtasks=[
            Task('get', V('object')),
            Task('go to', 'pot2'),
            Task('interact')
        ]
    ),
    # Method 9: Fallback
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[],
        subtasks=[
            Task('interact')
        ]
    )
]
```

#### C. Plate Method
**Before (commented out):**
```python
# domain["plate"] = [
#     Method(
#         name='plate',
#         preconditions=(),
#         subtasks=[
#             Task('get', 'dish'),
#             Task('go to', 'pot'),
#             Task('interact')
#         ]
#     ),
# ]
```

**After (7 active methods):**
```python
domain["plate"] = [
    # Method 1: Already have dish, plate from ready pot1
    Method(
        name='plate',
        preconditions=[
            Fact(player_holding='dish'),
            Fact(id='pot1', object='pot1', status='ready')
        ],
        subtasks=[
            Task('go to', 'pot1'),
            Task('interact')
        ]
    ),
    # Method 2: Already have dish, plate from ready pot2
    Method(
        name='plate',
        preconditions=[
            Fact(player_holding='dish'),
            Fact(id='pot2', object='pot2', status='ready')
        ],
        subtasks=[
            Task('go to', 'pot2'),
            Task('interact')
        ]
    ),
    # Method 3: Already have dish, plate from cooking pot1
    Method(
        name='plate',
        preconditions=[
            Fact(player_holding='dish'),
            Fact(id='pot1', object='pot1', status='cooking')
        ],
        subtasks=[
            Task('go to', 'pot1'),
            Task('interact')
        ]
    ),
    # Method 4: Already have dish, plate from cooking pot2
    Method(
        name='plate',
        preconditions=[
            Fact(player_holding='dish'),
            Fact(id='pot2', object='pot2', status='cooking')
        ],
        subtasks=[
            Task('go to', 'pot2'),
            Task('interact')
        ]
    ),
    # Method 5: Don't have dish, get it first, then plate from ready pot1
    Method(
        name='plate',
        preconditions=[
            NOT(Fact(player_holding='dish')),
            Fact(id='pot1', object='pot1', status='ready')
        ],
        subtasks=[
            Task('get', 'dish'),
            Task('go to', 'pot1'),
            Task('interact')
        ]
    ),
    # Method 6: Don't have dish, get it first, then plate from ready pot2
    Method(
        name='plate',
        preconditions=[
            NOT(Fact(player_holding='dish')),
            Fact(id='pot2', object='pot2', status='ready')
        ],
        subtasks=[
            Task('get', 'dish'),
            Task('go to', 'pot2'),
            Task('interact')
        ]
    ),
    # Method 7: Fallback
    Method(
        name='plate',
        preconditions=[],
        subtasks=[
            Task('get', 'dish'),
            Task('go to', 'pot'),
            Task('interact')
        ]
    ),
]
```

#### D. Deliver Method
**Before (WRONG NAME - was 'plate'):**
```python
domain["deliver"] = [
    Method(
        name='plate',  # BUG: Wrong name!
        preconditions=(),
        subtasks=[
            Task('go to', 'serving pad'),
            Task('interact')
        ]
    ),
]
```

**After (FIXED):**
```python
domain["deliver"] = [
    Method(
        name='deliver',  # FIXED: Correct name
        preconditions=(),
        subtasks=[
            Task('go to', 'serving pad'),
            Task('interact')
        ]
    ),
]
```

### 3. State Generation Changes

#### A. Player Holding State
**Before (BROKEN):**
```python
# No player holding state generated!
```

**After (FIXED):**
```python
# Add player holding status for HTN preconditions
if i == self.player_id:
    if player.held_object is None:
        state.append({'id': f'player_{i}_holding', 'player_holding': 'nothing'})
    else:
        state.append({'id': f'player_{i}_holding', 'player_holding': player.held_object.name})
```

#### B. Pot State
**Before (Generic pots only):**
```python
# Pots
pots = self.base_env.mdp.get_pot_states(self.base_env.state)

for x, y in pots['empty']:
    state.append({'id': f'pot_{x}_{y}', 'object': 'pot', 'x': x, 'y': y, 'status': 'empty',
                'onion': 0, 'tomato': 0})
for status in ['1_items', '2_items', '3_items', 'ready', 'cooking']:
    for x, y in pots[status]:
        state.append({'id': f'pot_{x}_{y}', 'object': 'pot', 'x': x, 'y': y, 'status': status})
```

**After (pot1 and pot2 distinction):**
```python
# Pots - Enhanced with pot1 and pot2 distinction
pots = self.base_env.mdp.get_pot_states(self.base_env.state)
pot_locations = self.base_env.mdp.get_pot_locations()

# Create pot1 and pot2 based on positions
pot1_pos = pot_locations[0] if len(pot_locations) > 0 else None
pot2_pos = pot_locations[1] if len(pot_locations) > 1 else None

# Add pot1 and pot2 as distinct objects for HTN
if pot1_pos:
    x, y = pot1_pos
    pot1_status = 'empty'
    for status in ['1_items', '2_items', '3_items', 'ready', 'cooking']:
        if pot1_pos in pots[status]:
            pot1_status = status
            break
    state.append({'id': 'pot1', 'object': 'pot1', 'x': x, 'y': y, 'status': pot1_status, 'position': pot1_pos})
    
if pot2_pos:
    x, y = pot2_pos
    pot2_status = 'empty'
    for status in ['1_items', '2_items', '3_items', 'ready', 'cooking']:
        if pot2_pos in pots[status]:
            pot2_status = status
            break
    state.append({'id': 'pot2', 'object': 'pot2', 'x': x, 'y': y, 'status': pot2_status, 'position': pot2_pos})

# Also add the original pot objects for compatibility
for x, y in pots['empty']:
    state.append({'id': f'pot_{x}_{y}', 'object': 'pot', 'x': x, 'y': y, 'status': 'empty',
                'onion': 0, 'tomato': 0})
for status in ['1_items', '2_items', '3_items', 'ready', 'cooking']:
    for x, y in pots[status]:
        state.append({'id': f'pot_{x}_{y}', 'object': 'pot', 'x': x, 'y': y, 'status': status})
        
# Add ready pots information for HTN preconditions
ready_pots = self.base_env.mdp.get_ready_pots(pots)
for x, y in ready_pots:
    state.append({'id': f'ready_pot_{x}_{y}', 'object': 'ready_pot', 'x': x, 'y': y, 'pot_id': f'pot_{x}_{y}'})
    
# Add ready pot1 and pot2 for HTN preconditions
if pot1_pos and pot1_pos in ready_pots:
    state.append({'id': 'ready_pot1', 'object': 'ready_pot1', 'x': pot1_pos[0], 'y': pot1_pos[1], 'pot_id': 'pot1'})
if pot2_pos and pot2_pos in ready_pots:
    state.append({'id': 'ready_pot2', 'object': 'ready_pot2', 'x': pot2_pos[0], 'y': pot2_pos[1], 'pot_id': 'pot2'})
```

### 4. Routing Changes

#### A. New Helper Method
**Added:**
```python
def _get_route_to_position(self, target_position):
    """
    Route to a specific position (x, y) - used for pot1/pot2 routing
    """
    pos, orr = self.get_player_pos_and_or()
    
    # Create a custom routing problem that targets a specific position
    class PositionRouteProblem(OvercookedRouteProblem):
        def __init__(self, initial_state, target_pos, extra):
            self.target_pos = target_pos
            super().__init__(initial_state, goal=None, extra=extra)
        
        def goal_test(self, state_node, goal_node=None):
            player_idx, pos, orr = state_node.state
            facing = (pos[0] + orr[0], pos[1] + orr[1])
            return facing == self.target_pos
    
    problem = PositionRouteProblem((self.player_id, pos, orr), target_position, self.base_env)
    try:
        sol = next(best_first_search(problem))
        return sol.path()
    except StopIteration:
        print(f"[ENV] Could not find route to position {target_position}")
        return None
```

#### B. Execute Action Enhancement
**Before:**
```python
def execute_action(self, action_name: str, args: List[str]) -> bool:
    if isinstance(args, tuple):
        args = list(args)
    print(f"[ENV] Executing: {action_name}({args})")

    if action_name == "go to" and len(args) == 1:
        action_plan = self.get_route_plan(args[0])
        for action in action_plan:
            command = [(0, 0) for _ in self.base_env.state.players]
            command[self.player_id] = action
            self.base_env.step(command)
    # ... rest of method
```

**After:**
```python
def execute_action(self, action_name: str, args: List[str]) -> bool:
    if isinstance(args, tuple):
        args = list(args)
    print(f"[ENV] Executing: {action_name}({args})")

    if action_name == "go to" and len(args) == 1:
        target = args[0]
        
        # Handle specific pot routing for pot1, pot2, ready_pot1, ready_pot2
        if target in ['pot1', 'pot2', 'ready_pot1', 'ready_pot2']:
            pot_locations = self.base_env.mdp.get_pot_locations()
            
            if target in ['pot1', 'ready_pot1'] and len(pot_locations) > 0:
                pot1_pos = pot_locations[0]
                print(f"[ENV] Routing to pot1 at position {pot1_pos}")
                action_plan = self._get_route_to_position(pot1_pos)
            elif target in ['pot2', 'ready_pot2'] and len(pot_locations) > 1:
                pot2_pos = pot_locations[1]
                print(f"[ENV] Routing to pot2 at position {pot2_pos}")
                action_plan = self._get_route_to_position(pot2_pos)
            else:
                print(f"[ENV] Fallback: routing to generic pot for {target}")
                action_plan = self.get_route_plan('pot')
        else:
            action_plan = self.get_route_plan(target)
        
        if action_plan:
            for action in action_plan:
                command = [(0, 0) for _ in self.base_env.state.players]
                command[self.player_id] = action
                self.base_env.step(command)
        else:
            print(f"[ENV] Could not find route to {target}")
            return False
    # ... rest of method
```

### 5. Configuration Changes

**Before:**
```python
def __init__(self, player_id=0, horizon=100, layout="asymmetric_advantages", render=True):
    self.player_id = 0  # Hardcoded to 0
```

**After:**
```python
def __init__(self, player_id=0, horizon=100, layout="asymmetric_advantages", render=True):
    self.player_id = player_id  # Uses parameter
```

## 🎯 Impact Summary

### Behavior Changes:
1. **Agent now says which pot**: "go to pot1" instead of "go to pot"
2. **No redundant gets**: Won't try to get ingredient if already holding it
3. **Smart pot selection**: Goes to ready pot for plating, empty pot for boiling
4. **No infinite loops**: Fixed player_holding fact format prevents recursion

### Performance Improvements:
1. **Fewer failed actions**: Preconditions prevent invalid method selection
2. **More efficient paths**: Direct routing to specific pots
3. **Better resource usage**: Can use both pots effectively

### Code Quality:
1. **More maintainable**: Clear preconditions document method requirements
2. **More extensible**: Easy to add new pot-specific behaviors
3. **Better debugging**: Explicit pot names make logs clearer

## 🔄 Migration Steps

1. **Backup current file**
2. **Copy enhanced version**
3. **Test with simple commands**: "cook onion"
4. **Verify pot distinction**: Check logs for "pot1" and "pot2"
5. **Test edge cases**: Player already holding ingredient

---

**Total Lines Changed:** ~300 lines  
**New Methods Added:** 1 (`_get_route_to_position`)  
**HTN Methods Enhanced:** 3 (boil, plate, deliver)  
**State Facts Added:** 6+ (player_holding, pot1, pot2, ready_pot1, ready_pot2, etc.)

