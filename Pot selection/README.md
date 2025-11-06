# Pot Selection Logic - Enhanced HTN System

## 📋 Overview

This folder contains the enhanced version of the Overcooked AI environment with **intelligent pot selection logic** and **player holding state awareness**. The system can now distinguish between multiple pots (pot1 and pot2) and make smart decisions about which pot to use based on preconditions.

## 🎯 Key Features

### 1. **Pot Distinction (pot1 vs pot2)**
- The system now treats pots as distinct entities instead of generic "pot" objects
- pot1 = first pot in the layout
- pot2 = second pot in the layout
- Agent explicitly states which pot it's going to (e.g., "go to pot1" instead of "go to pot")

### 2. **Player Holding State Awareness**
- HTN methods now check if the player is already holding an ingredient
- Prevents redundant "get" actions when player already has the object
- **CRITICAL FIX**: Changed state fact format from `Fact(object='player_holding', status='onion')` to `Fact(player_holding='onion')` to match HTN preconditions

### 3. **Intelligent Boil Method Selection**
The `boil` method now has 9 different implementations based on:
- Whether player is holding the ingredient
- Which pot is empty (pot1 or pot2)
- Which pot has 1 item (ready to complete recipe)

### 4. **Intelligent Plate Method Selection**
The `plate` method now has 7 different implementations based on:
- Whether player is holding a dish
- Which pot has ready soup (pot1 or pot2)
- Which pot is cooking (pot1 or pot2)

### 5. **Position-Based Routing**
- New `_get_route_to_position()` method for routing to specific pot positions
- Enhanced `execute_action()` to handle pot1/pot2/ready_pot1/ready_pot2 routing

## 📁 Files in This Folder

### `overcooked_ai_env.py`
The main enhanced environment file with all pot selection logic.

**Key Changes:**

#### A. Enhanced HTN Methods

**Boil Methods (9 variants):**
```python
# Method 1-4: Player already holding object
- Fact(player_holding=V('object'))  # PRIORITY precondition
- Checks pot1 or pot2 empty/1_items status

# Method 5-8: Player doesn't have object yet
- NOT(Fact(player_holding=V('object')))
- Includes Task('get', V('object')) first
- Then routes to appropriate pot

# Method 9: Fallback
- No preconditions
- Just interact (for when already at pot)
```

**Plate Methods (7 variants):**
```python
# Method 1-4: Player already holding dish
- Fact(player_holding='dish')
- Routes to pot1/pot2 based on ready/cooking status

# Method 5-6: Player doesn't have dish
- NOT(Fact(player_holding='dish'))
- Gets dish first, then routes to ready pot

# Method 7: Fallback
- Generic pot routing
```

#### B. Enhanced State Generation

**Player Holding Facts:**
```python
# OLD (BROKEN):
state.append({'id': 'player_0_holding', 'object': 'player_holding', 'status': 'onion'})

# NEW (FIXED):
state.append({'id': 'player_0_holding', 'player_holding': 'onion'})
```

**Pot Distinction:**
```python
# pot1 and pot2 as distinct objects
pot1_pos = pot_locations[0]
pot2_pos = pot_locations[1]

state.append({'id': 'pot1', 'object': 'pot1', 'x': x, 'y': y, 'status': pot1_status, 'position': pot1_pos})
state.append({'id': 'pot2', 'object': 'pot2', 'x': x, 'y': y, 'status': pot2_status, 'position': pot2_pos})
```

#### C. Enhanced Routing

**Position-Based Routing:**
```python
def _get_route_to_position(self, target_position):
    """Route to a specific (x, y) position"""
    class PositionRouteProblem(OvercookedRouteProblem):
        def goal_test(self, state_node, goal_node=None):
            player_idx, pos, orr = state_node.state
            facing = (pos[0] + orr[0], pos[1] + orr[1])
            return facing == self.target_pos
```

**Execute Action Enhancement:**
```python
if target in ['pot1', 'pot2', 'ready_pot1', 'ready_pot2']:
    pot_locations = self.base_env.mdp.get_pot_locations()
    
    if target in ['pot1', 'ready_pot1']:
        pot1_pos = pot_locations[0]
        action_plan = self._get_route_to_position(pot1_pos)
    elif target in ['pot2', 'ready_pot2']:
        pot2_pos = pot_locations[1]
        action_plan = self._get_route_to_position(pot2_pos)
```

## 🔧 How to Use

### 1. Replace the current environment file:
```bash
cp "Pot selection/overcooked_ai_env.py" "val/env_interfaces/overcooked_ai/overcooked_ai_env.py"
```

### 2. Test the system:
```python
from val.env_interfaces.overcooked_ai.overcooked_ai_env import OvercookedAIEnv

env = OvercookedAIEnv(player_id=0, horizon=100, layout="asymmetric_advantages")
state = env.get_state()

# Check pot distinction
for fact in state:
    if 'pot1' in str(fact) or 'pot2' in str(fact):
        print(fact)

# Check player holding
for fact in state:
    if 'player_holding' in fact:
        print(fact)
```

## 🐛 Bug Fixes

### Issue 1: Infinite Recursion Loop
**Problem:** Agent kept trying to `get(onion)` even when already holding onion.

**Root Cause:** State fact format mismatch
- State generated: `{'object': 'player_holding', 'status': 'onion'}`
- HTN expected: `Fact(player_holding='onion')`

**Solution:** Changed state generation to match HTN format:
```python
state.append({'id': f'player_{i}_holding', 'player_holding': player.held_object.name})
```

### Issue 2: Generic Pot Routing
**Problem:** Agent couldn't distinguish between pots, always went to nearest pot.

**Solution:** 
- Added pot1 and pot2 as distinct state facts
- Created position-based routing for specific pots
- Enhanced HTN methods with pot-specific preconditions

### Issue 3: Redundant Get Actions
**Problem:** Agent would try to get ingredient even when already holding it.

**Solution:**
- Added `Fact(player_holding=V('object'))` preconditions for "already holding" methods
- Added `NOT(Fact(player_holding=V('object')))` preconditions for "need to get" methods
- Prioritized "already holding" methods by placing them first

## 📊 Comparison: Before vs After

### Before (Simple Version):
```python
domain["boil"] = [
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[],
        subtasks=[
            Task('go to', 'pot'),  # Generic pot
            Task('interact')
        ]
    )
]

# State:
state.append({'id': 'pot_3_2', 'object': 'pot', 'status': 'empty'})
```

### After (Enhanced Version):
```python
domain["boil"] = [
    # 9 different methods with specific preconditions
    Method(
        name='boil',
        args=(V('object'),),
        preconditions=[
            Fact(player_holding=V('object')),  # Already holding
            Fact(id='pot1', object='pot1', status='empty')  # Specific pot
        ],
        subtasks=[
            Task('go to', 'pot1'),  # Explicit pot1
            Task('interact')
        ]
    ),
    # ... 8 more variants
]

# State:
state.append({'id': 'pot1', 'object': 'pot1', 'status': 'empty', 'position': (3, 2)})
state.append({'id': 'pot2', 'object': 'pot2', 'status': '1_items', 'position': (5, 2)})
state.append({'id': 'player_0_holding', 'player_holding': 'onion'})
```

## 🎓 Learning Points

### 1. **HTN Fact Format is Critical**
The fact format in state generation MUST exactly match the format expected in HTN preconditions:
```python
# HTN expects:
Fact(player_holding='onion')

# State must provide:
{'player_holding': 'onion'}  # NOT {'object': 'player_holding', 'status': 'onion'}
```

### 2. **Precondition Order Matters**
Methods with more specific preconditions should come first:
```python
# Good: Specific first
Method(preconditions=[Fact(player_holding='onion'), Fact(pot1='empty')])
Method(preconditions=[Fact(player_holding='onion')])
Method(preconditions=[])  # Fallback last

# Bad: Fallback first would always match
Method(preconditions=[])  # Would always be selected!
Method(preconditions=[Fact(player_holding='onion')])
```

### 3. **NOT() Conditions for Negation**
Use `NOT(Fact(...))` to check for absence:
```python
NOT(Fact(player_holding=V('object')))  # Player NOT holding object
```

### 4. **Position-Based Routing for Identical Objects**
When objects are identical in the MDP but need distinction in HTN:
- Create virtual names (pot1, pot2) in state
- Use position-based routing to actual coordinates
- Map virtual names to positions in execute_action

## 🚀 Future Enhancements

1. **Dynamic Pot Selection**
   - Choose pot based on proximity
   - Choose pot based on current contents
   - Parallel cooking in both pots

2. **Multi-Agent Coordination**
   - Avoid pot conflicts
   - Coordinate ingredient gathering
   - Load balancing across pots

3. **Recipe-Aware Selection**
   - Match ingredients in pot with order requirements
   - Optimize for order completion time

4. **XAI Integration**
   - Explain why specific pot was chosen
   - Show precondition satisfaction details

## 📝 Notes

- Layout used: `asymmetric_advantages` (has 2 pots)
- Player ID: 0 (first player)
- Horizon: 100 timesteps
- Render: True (visual feedback enabled)

## 🔗 Related Files

If you also have enhanced versions of these files, they should be added here:
- `val/htn_interfaces/py_htn_interface.py` (for get_tasks() fix)
- `val/agent.py` (for XAI enhancements)
- `val/prompts/newprompts/1st try.txt` (for XAI prompt)

## ⚠️ Important Warnings

1. **Don't remove `player_holding` facts** - They are critical for preventing infinite loops
2. **Don't change fact format** - Must match HTN preconditions exactly
3. **Don't reorder methods** - Specific preconditions must come before generic ones
4. **Don't remove pot1/pot2 distinction** - Needed for intelligent pot selection

## 📞 Contact

If you have questions about this implementation, refer to the conversation history where we:
1. Simplified the HTN structure
2. Added pot distinction (pot1 and pot2)
3. Fixed the player_holding fact format bug
4. Enhanced boil and plate methods with preconditions
5. Removed wait tasks from boil methods
6. Cleaned up debug statements
7. Fixed the infinite recursion issue

---

**Version:** 1.0  
**Date:** 2025-11-06  
**Status:** ✅ Tested and Working

