# Architecture Overview - Pot Selection System

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         VAL Agent System                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HTN Planner (PyHTN)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Task: cook(onion)                                        │  │
│  │    ├─ get(onion)                                          │  │
│  │    ├─ boil(onion)  ◄─── ENHANCED with pot selection     │  │
│  │    ├─ get(dish)                                           │  │
│  │    ├─ plate()      ◄─── ENHANCED with pot selection     │  │
│  │    └─ deliver()                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              OvercookedAIEnv (Enhanced Version)                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  State Generation:                                        │  │
│  │    • player_holding facts  ◄─── NEW                      │  │
│  │    • pot1 facts           ◄─── NEW                      │  │
│  │    • pot2 facts           ◄─── NEW                      │  │
│  │    • ready_pot1/pot2      ◄─── NEW                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  HTN Methods:                                             │  │
│  │    • 9 boil methods       ◄─── ENHANCED (was 3)         │  │
│  │    • 7 plate methods      ◄─── ENHANCED (was 0)         │  │
│  │    • Preconditions        ◄─── NEW                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Routing:                                                 │  │
│  │    • Position-based routing ◄─── NEW                    │  │
│  │    • pot1/pot2 specific    ◄─── NEW                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Overcooked AI MDP (Base Environment)               │
│  • Pot states (empty, 1_items, cooking, ready)                 │
│  • Player positions and orientations                            │
│  • Object locations (onion, dish, tomato, etc.)                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow

### 1. State Generation Flow

```
Overcooked MDP State
        │
        ▼
┌───────────────────────────────────────┐
│  get_state()                          │
│  ┌─────────────────────────────────┐ │
│  │ 1. Get pot locations            │ │
│  │    pot_locations = mdp.get_pot_ │ │
│  │    locations()                  │ │
│  │                                 │ │
│  │ 2. Assign pot1 and pot2         │ │
│  │    pot1_pos = pot_locations[0]  │ │
│  │    pot2_pos = pot_locations[1]  │ │
│  │                                 │ │
│  │ 3. Get pot states               │ │
│  │    pots = mdp.get_pot_states()  │ │
│  │                                 │ │
│  │ 4. Generate pot facts           │ │
│  │    Fact(id='pot1', status=...)  │ │
│  │    Fact(id='pot2', status=...)  │ │
│  │                                 │ │
│  │ 5. Get player holding           │ │
│  │    player.held_object.name      │ │
│  │                                 │ │
│  │ 6. Generate holding fact        │ │
│  │    Fact(player_holding='onion') │ │
│  └─────────────────────────────────┘ │
└───────────────────────────────────────┘
        │
        ▼
HTN Facts for Planner
```

### 2. Method Selection Flow

```
Task: boil(onion)
        │
        ▼
┌───────────────────────────────────────┐
│  HTN Planner Checks Preconditions     │
│  ┌─────────────────────────────────┐ │
│  │ Method 1:                       │ │
│  │   ✓ player_holding='onion'      │ │
│  │   ✓ pot1.status='empty'         │ │
│  │   → SELECTED!                   │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │ Method 2:                       │ │
│  │   ✓ player_holding='onion'      │ │
│  │   ✗ pot2.status='empty'         │ │
│  │   → SKIPPED                     │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │ Method 5:                       │ │
│  │   ✗ NOT(player_holding='onion') │ │
│  │   → SKIPPED                     │ │
│  └─────────────────────────────────┘ │
└───────────────────────────────────────┘
        │
        ▼
Subtasks: [go to('pot1'), interact()]
```

### 3. Action Execution Flow

```
Subtask: go to('pot1')
        │
        ▼
┌───────────────────────────────────────┐
│  execute_action('go to', ['pot1'])    │
│  ┌─────────────────────────────────┐ │
│  │ 1. Check if target is pot1/pot2 │ │
│  │    if target == 'pot1':         │ │
│  │                                 │ │
│  │ 2. Get pot locations            │ │
│  │    pot_locations = mdp.get_pot_ │ │
│  │    locations()                  │ │
│  │                                 │ │
│  │ 3. Get pot1 position            │ │
│  │    pot1_pos = pot_locations[0]  │ │
│  │                                 │ │
│  │ 4. Route to position            │ │
│  │    action_plan = _get_route_to_ │ │
│  │    position(pot1_pos)           │ │
│  │                                 │ │
│  │ 5. Execute movement             │ │
│  │    for action in action_plan:   │ │
│  │      base_env.step(action)      │ │
│  └─────────────────────────────────┘ │
└───────────────────────────────────────┘
        │
        ▼
Agent moves to pot1
```

## 🎯 Method Selection Decision Tree

### Boil Method Selection

```
boil(onion)
    │
    ├─ Is player holding onion?
    │   │
    │   ├─ YES ─┐
    │   │       │
    │   │       ├─ Is pot1 empty?
    │   │       │   YES → Method 1: [go to pot1, interact]
    │   │       │
    │   │       ├─ Is pot2 empty?
    │   │       │   YES → Method 2: [go to pot2, interact]
    │   │       │
    │   │       ├─ Is pot1 has 1_items?
    │   │       │   YES → Method 3: [go to pot1, interact]
    │   │       │
    │   │       └─ Is pot2 has 1_items?
    │   │           YES → Method 4: [go to pot2, interact]
    │   │
    │   └─ NO ──┐
    │           │
    │           ├─ Is pot1 empty?
    │           │   YES → Method 5: [get onion, go to pot1, interact]
    │           │
    │           ├─ Is pot2 empty?
    │           │   YES → Method 6: [get onion, go to pot2, interact]
    │           │
    │           ├─ Is pot1 has 1_items?
    │           │   YES → Method 7: [get onion, go to pot1, interact]
    │           │
    │           └─ Is pot2 has 1_items?
    │               YES → Method 8: [get onion, go to pot2, interact]
    │
    └─ No preconditions match?
        → Method 9 (Fallback): [interact]
```

### Plate Method Selection

```
plate()
    │
    ├─ Is player holding dish?
    │   │
    │   ├─ YES ─┐
    │   │       │
    │   │       ├─ Is pot1 ready?
    │   │       │   YES → Method 1: [go to pot1, interact]
    │   │       │
    │   │       ├─ Is pot2 ready?
    │   │       │   YES → Method 2: [go to pot2, interact]
    │   │       │
    │   │       ├─ Is pot1 cooking?
    │   │       │   YES → Method 3: [go to pot1, interact]
    │   │       │
    │   │       └─ Is pot2 cooking?
    │   │           YES → Method 4: [go to pot2, interact]
    │   │
    │   └─ NO ──┐
    │           │
    │           ├─ Is pot1 ready?
    │           │   YES → Method 5: [get dish, go to pot1, interact]
    │           │
    │           └─ Is pot2 ready?
    │               YES → Method 6: [get dish, go to pot2, interact]
    │
    └─ No preconditions match?
        → Method 7 (Fallback): [get dish, go to pot, interact]
```

## 🔧 Component Interactions

### State Facts → HTN Preconditions

```
State Fact Format              HTN Precondition Format
─────────────────              ───────────────────────
{'player_holding': 'onion'}  → Fact(player_holding='onion')
{'id': 'pot1',               → Fact(id='pot1',
 'object': 'pot1',              object='pot1',
 'status': 'empty'}             status='empty')
{'id': 'pot2',               → Fact(id='pot2',
 'object': 'pot2',              object='pot2',
 'status': 'ready'}             status='ready')
```

**CRITICAL:** The keys in state facts MUST match the parameter names in HTN Facts!

### HTN Tasks → Environment Actions

```
HTN Task                    Environment Action
────────                    ──────────────────
Task('go to', 'pot1')    → execute_action('go to', ['pot1'])
                           → _get_route_to_position(pot1_pos)
                           → base_env.step(actions)

Task('interact')         → execute_action('interact', [])
                           → base_env.step('interact')

Task('get', 'onion')     → execute_action('get', ['onion'])
                           → [Decomposed to: go to(onion), interact()]
```

## 📊 State Space

### Pot States
```
empty       → No ingredients
1_items     → One ingredient added
2_items     → Two ingredients added (for 3-ingredient soups)
3_items     → Three ingredients added (for 3-ingredient soups)
cooking     → Recipe complete, cooking in progress
ready       → Cooking complete, ready to plate
```

### Player Holding States
```
nothing     → Not holding anything
onion       → Holding an onion
tomato      → Holding a tomato
dish        → Holding a dish
soup        → Holding plated soup
```

### Pot Combinations (2 pots)
```
pot1: empty,    pot2: empty     → Both available
pot1: 1_items,  pot2: empty     → pot1 has onion, pot2 available
pot1: cooking,  pot2: empty     → pot1 cooking, pot2 available
pot1: ready,    pot2: cooking   → pot1 ready to plate, pot2 cooking
pot1: empty,    pot2: ready     → pot1 available, pot2 ready to plate
```

## 🎮 Example Scenario Walkthrough

### Scenario: Cook Onion Soup

```
Initial State:
  player_holding: nothing
  pot1: empty
  pot2: empty

Step 1: cook(onion)
  ├─ Decomposed to: [get(onion), boil(onion), get(dish), plate(), deliver()]

Step 2: get(onion)
  ├─ Decomposed to: [go to(onion), interact()]
  ├─ Execute: go to(onion)
  └─ Execute: interact()
  Result: player_holding = onion

Step 3: boil(onion)
  ├─ Check preconditions:
  │   ✓ player_holding = onion
  │   ✓ pot1 = empty
  ├─ Selected: Method 1
  ├─ Decomposed to: [go to(pot1), interact()]
  ├─ Execute: go to(pot1)
  │   └─ Routes to position (3, 2)
  └─ Execute: interact()
  Result: pot1 = 1_items, player_holding = nothing

Step 4: get(dish)
  ├─ Decomposed to: [go to(dish), interact()]
  ├─ Execute: go to(dish)
  └─ Execute: interact()
  Result: player_holding = dish

Step 5: Wait for cooking...
  (pot1 automatically cooks and becomes ready)
  Result: pot1 = ready

Step 6: plate()
  ├─ Check preconditions:
  │   ✓ player_holding = dish
  │   ✓ pot1 = ready
  ├─ Selected: Method 1
  ├─ Decomposed to: [go to(pot1), interact()]
  ├─ Execute: go to(pot1)
  │   └─ Routes to position (3, 2)
  └─ Execute: interact()
  Result: player_holding = soup, pot1 = empty

Step 7: deliver()
  ├─ Decomposed to: [go to(serving pad), interact()]
  ├─ Execute: go to(serving pad)
  └─ Execute: interact()
  Result: Order completed! 🎉
```

## 🔍 Key Design Patterns

### 1. **Priority-Based Method Selection**
Methods with more specific preconditions are listed first, ensuring the most appropriate method is selected.

### 2. **State-Aware Preconditions**
Preconditions check both player state (holding) and environment state (pot status).

### 3. **Position-Based Object Distinction**
Identical objects (pots) are distinguished by their positions in the layout.

### 4. **Hierarchical Task Decomposition**
High-level tasks (cook) decompose into mid-level tasks (boil, plate) which decompose into low-level actions (go to, interact).

### 5. **Fact Format Consistency**
State generation produces facts in the exact format expected by HTN preconditions.

---

**This architecture enables:**
- ✅ Intelligent pot selection
- ✅ No redundant actions
- ✅ Clear decision-making logic
- ✅ Extensible design
- ✅ Transparent behavior

