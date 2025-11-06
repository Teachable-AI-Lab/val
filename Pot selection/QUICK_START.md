# Quick Start Guide - Pot Selection Logic

## 🚀 5-Minute Setup

### Step 1: Backup Current File
```bash
cd val/env_interfaces/overcooked_ai/
cp overcooked_ai_env.py overcooked_ai_env_backup.py
```

### Step 2: Replace with Enhanced Version
```bash
# From the root of your project
cp "Pot selection/overcooked_ai_env.py" "val/env_interfaces/overcooked_ai/overcooked_ai_env.py"
```

### Step 3: Test It!
```python
from val.env_interfaces.overcooked_ai.overcooked_ai_env import OvercookedAIEnv

# Create environment
env = OvercookedAIEnv(player_id=0, horizon=100, layout="asymmetric_advantages", render=True)

# Get state and check pot distinction
state = env.get_state()

print("=== Pot Facts ===")
for fact in state:
    if 'pot1' in str(fact) or 'pot2' in str(fact):
        print(fact)

print("\n=== Player Holding Facts ===")
for fact in state:
    if 'player_holding' in fact:
        print(fact)

# Get actions and check HTN methods
domain, descriptions = env.get_actions()

print("\n=== Boil Methods ===")
print(f"Number of boil methods: {len(domain['boil'])}")
for i, method in enumerate(domain['boil']):
    print(f"Method {i+1}: {len(method.preconditions)} preconditions, {len(method.subtasks)} subtasks")

print("\n=== Plate Methods ===")
print(f"Number of plate methods: {len(domain['plate'])}")
for i, method in enumerate(domain['plate']):
    print(f"Method {i+1}: {len(method.preconditions)} preconditions, {len(method.subtasks)} subtasks")
```

**Expected Output:**
```
=== Pot Facts ===
{'id': 'pot1', 'object': 'pot1', 'x': 3, 'y': 2, 'status': 'empty', 'position': (3, 2)}
{'id': 'pot2', 'object': 'pot2', 'x': 5, 'y': 2, 'status': 'empty', 'position': (5, 2)}

=== Player Holding Facts ===
{'id': 'player_0_holding', 'player_holding': 'nothing'}

=== Boil Methods ===
Number of boil methods: 9
Method 1: 2 preconditions, 2 subtasks
Method 2: 2 preconditions, 2 subtasks
...

=== Plate Methods ===
Number of plate methods: 7
Method 1: 2 preconditions, 2 subtasks
...
```

## 🎮 Test Scenarios

### Scenario 1: Cook Onion (Full Workflow)
```python
env = OvercookedAIEnv(player_id=0, horizon=100, layout="asymmetric_advantages", render=True)

# Execute cook onion command
# This will:
# 1. Get onion
# 2. Boil onion (should say "go to pot1" or "go to pot2")
# 3. Get dish
# 4. Plate (should say "go to pot1" or "go to pot2" based on which is ready)
# 5. Deliver

# Watch the console output - you should see explicit pot names!
```

### Scenario 2: Test Player Holding Logic
```python
env = OvercookedAIEnv(player_id=0, horizon=100, layout="asymmetric_advantages", render=True)

# Step 1: Get onion
env.execute_action("go to", ['onion'])
env.execute_action("interact", [])

# Step 2: Check state
state = env.get_state()
for fact in state:
    if 'player_holding' in fact:
        print(f"Player holding: {fact}")
        # Should show: {'id': 'player_0_holding', 'player_holding': 'onion'}

# Step 3: Try to boil
# The HTN should select a method with Fact(player_holding='onion') precondition
# It should NOT try to get onion again!
```

### Scenario 3: Test Pot Selection
```python
env = OvercookedAIEnv(player_id=0, horizon=100, layout="asymmetric_advantages", render=True)

# Get onion
env.execute_action("go to", ['onion'])
env.execute_action("interact", [])

# Go to pot1 specifically
env.execute_action("go to", ['pot1'])
print("Should route to pot1 position")

# Go to pot2 specifically
env.execute_action("go to", ['pot2'])
print("Should route to pot2 position")
```

## 🔍 Verification Checklist

After installing the enhanced version, verify:

- [ ] **Pot Distinction**: State contains `pot1` and `pot2` facts
- [ ] **Player Holding**: State contains `player_holding` fact
- [ ] **Boil Methods**: 9 methods (not 3)
- [ ] **Plate Methods**: 7 methods (not commented out)
- [ ] **Deliver Method**: Named `deliver` (not `plate`)
- [ ] **Routing**: Can route to `pot1` and `pot2` specifically
- [ ] **No Infinite Loops**: Agent doesn't repeatedly try to get already-held items

## 🐛 Troubleshooting

### Issue: "AttributeError: 'OvercookedRouteProblem' object has no attribute 'base_env'"
**Solution:** Make sure you're using the enhanced version with the `_get_route_to_position` method.

### Issue: Agent keeps trying to get onion even when holding it
**Solution:** Check that `player_holding` facts are being generated correctly:
```python
state = env.get_state()
holding_facts = [f for f in state if 'player_holding' in f]
print(holding_facts)
# Should show: [{'id': 'player_0_holding', 'player_holding': 'onion'}]
# NOT: [{'object': 'player_holding', 'status': 'onion'}]
```

### Issue: Agent always goes to the same pot
**Solution:** Check that pot1 and pot2 facts are being generated:
```python
state = env.get_state()
pot_facts = [f for f in state if f.get('object') in ['pot1', 'pot2']]
print(pot_facts)
# Should show both pot1 and pot2 with their positions and statuses
```

### Issue: "Could not find route to pot1"
**Solution:** Make sure the layout has at least 2 pots. Use `asymmetric_advantages` layout which has 2 pots.

## 📊 Performance Comparison

Run this test to compare behavior:

```python
import time

# Test with simple version (backup)
env_simple = OvercookedAIEnv(player_id=0, horizon=100)
start = time.time()
# Execute cook onion
# Count number of actions
simple_actions = 0  # Count manually
simple_time = time.time() - start

# Test with enhanced version
env_enhanced = OvercookedAIEnv(player_id=0, horizon=100)
start = time.time()
# Execute cook onion
# Count number of actions
enhanced_actions = 0  # Count manually
enhanced_time = time.time() - start

print(f"Simple: {simple_actions} actions in {simple_time:.2f}s")
print(f"Enhanced: {enhanced_actions} actions in {enhanced_time:.2f}s")
print(f"Improvement: {(simple_actions - enhanced_actions) / simple_actions * 100:.1f}% fewer actions")
```

## 🎯 Key Behaviors to Observe

### 1. Explicit Pot Naming
**Before:**
```
[ENV] Executing: go to(['pot'])
```

**After:**
```
[ENV] Executing: go to(['pot1'])
[ENV] Routing to pot1 at position (3, 2)
```

### 2. No Redundant Gets
**Before:**
```
get(onion) → go to(onion) → interact
boil(onion) → get(onion) → go to(onion) → interact → ...  # REDUNDANT!
```

**After:**
```
get(onion) → go to(onion) → interact
boil(onion) → go to(pot1) → interact  # No redundant get!
```

### 3. Smart Pot Selection for Plating
**Before:**
```
plate() → get(dish) → go to(pot) → interact  # Goes to nearest pot
```

**After:**
```
plate() → get(dish) → go to(pot2) → interact  # Goes to pot2 because it's ready!
```

## 📝 Next Steps

1. **Test with your agent**: Run your full agent system with the enhanced environment
2. **Monitor logs**: Watch for explicit pot1/pot2 references
3. **Test edge cases**: Try scenarios with both pots full, both empty, etc.
4. **Integrate XAI**: If you have XAI enhancements, they will now show detailed preconditions

## 🔗 Additional Resources

- **README.md**: Full documentation of all features
- **CHANGES_SUMMARY.md**: Detailed line-by-line comparison
- **overcooked_ai_env.py**: The enhanced environment file

## ⚠️ Important Notes

1. **Layout Requirement**: Use layouts with 2+ pots (e.g., `asymmetric_advantages`)
2. **Player ID**: Make sure `player_id` parameter is used (not hardcoded to 0)
3. **Fact Format**: The `player_holding` fact format is critical - don't modify it
4. **Method Order**: Don't reorder HTN methods - specific preconditions must come first

## 🎉 Success Indicators

You'll know it's working when you see:
- ✅ Console logs showing "pot1" and "pot2" explicitly
- ✅ Agent doesn't try to get items it's already holding
- ✅ Agent selects pots intelligently based on state
- ✅ No infinite loops or repeated failed actions
- ✅ Plating goes to ready pots, not just nearest pot

---

**Need Help?** Check the README.md for detailed explanations of each feature.

**Found a Bug?** Compare your version with the provided `overcooked_ai_env.py` file line by line.

**Want to Extend?** The system is designed to be extensible - add more preconditions or methods as needed!

