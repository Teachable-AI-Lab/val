#!/usr/bin/env python3
"""
Standalone test for precondition parsing logic
Tests the regex patterns and parsing logic without external dependencies
"""

import re

class MockFact:
    def __init__(self, name, operator, value):
        self.name = name
        self.operator = operator
        self.value = value
    
    def __str__(self):
        return f"Fact({self.name} {self.operator} {self.value})"

def rule_based_precondition_parsing(chatbot_response: str, task_name: str):
    """
    Rule-based parsing for common precondition patterns
    """
    preconditions = []
    response_lower = chatbot_response.lower()
    
    # Common precondition patterns
    patterns = [
        # Resource availability
        (r'need\s+(\w+)\s*[>=]\s*(\d+)', 'resource_check', '>='),
        (r'require\s+(\w+)\s*[>=]\s*(\d+)', 'resource_check', '>='),
        (r'at\s+least\s+(\d+)\s+(\w+)', 'resource_check', '>='),
        (r'more\s+than\s+(\d+)\s+(\w+)', 'resource_check', '>'),
        
        # State conditions
        (r'(\w+)\s+must\s+be\s+(\w+)', 'state_check', '='),
        (r'(\w+)\s+should\s+be\s+(\w+)', 'state_check', '='),
        (r'(\w+)\s+is\s+(\w+)', 'state_check', '='),
        
        # Boolean conditions
        (r'(\w+)\s+available', 'availability', '='),
        (r'(\w+)\s+ready', 'readiness', '='),
        (r'(\w+)\s+empty', 'emptiness', '='),
    ]
    
    for pattern, fact_type, operator in patterns:
        matches = re.findall(pattern, response_lower)
        for match in matches:
            if fact_type == 'resource_check':
                if len(match) == 2:
                    value, resource = match
                    try:
                        value = int(value)
                        fact_name = f"{resource}_count"
                        preconditions.append(MockFact(fact_name, operator, value))
                    except ValueError:
                        continue
            elif fact_type == 'state_check':
                if len(match) == 2:
                    object_name, state = match
                    fact_name = f"{object_name}_state"
                    preconditions.append(MockFact(fact_name, operator, state))
            elif fact_type in ['availability', 'readiness', 'emptiness']:
                if len(match) == 1:
                    object_name = match[0]
                    fact_name = f"{object_name}_{fact_type}"
                    preconditions.append(MockFact(fact_name, operator, True))
    
    # Special case: check for negation patterns
    neg_patterns = [
        (r'no\s+(\w+)', 'resource_check', '='),
        (r'(\w+)\s+not\s+(\w+)', 'state_check', '!='),
    ]
    
    for pattern, fact_type, operator in neg_patterns:
        matches = re.findall(pattern, response_lower)
        for match in matches:
            if fact_type == 'resource_check':
                if len(match) == 1:
                    resource = match[0]
                    fact_name = f"{resource}_count"
                    preconditions.append(MockFact(fact_name, operator, 0))
            elif fact_type == 'state_check':
                if len(match) == 2:
                    object_name, state = match
                    fact_name = f"{object_name}_state"
                    preconditions.append(MockFact(fact_name, operator, state))
    
    return preconditions

def test_rule_based_parsing():
    """Test the rule-based precondition parsing"""
    print("🧪 Testing Rule-based Precondition Parsing...")
    
    # Test cases
    test_cases = [
        ("I need at least 3 onions to cook", "cook"),
        ("The pot must be empty before adding ingredients", "add_ingredients"),
        ("We require more than 2 tomatoes", "cook"),
        ("The stove should be ready and available", "cook"),
        ("No other ingredients should be in the pot", "cook"),
        ("The kitchen must be clean", "prepare_meal"),
        ("I need 2 onions", "cook"),
        ("The pot is empty", "cook"),
        ("The stove is ready", "cook"),
        ("No onions in the pot", "cook"),
        ("The chef is not certified", "cook"),
    ]
    
    for response, task_name in test_cases:
        print(f"\n📝 Input: '{response}'")
        try:
            preconditions = rule_based_precondition_parsing(response, task_name)
            if preconditions:
                print(f"✅ Found {len(preconditions)} preconditions:")
                for fact in preconditions:
                    print(f"   - {fact}")
            else:
                print("❌ No preconditions found")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_edge_cases():
    """Test edge cases and complex scenarios"""
    print("\n🧪 Testing Edge Cases...")
    
    edge_cases = [
        ("Need exactly 5 onions and 3 tomatoes", "cook"),
        ("The temperature must be between 180-200 degrees", "cook"),
        ("Multiple conditions: pot empty, stove ready, chef certified", "cook"),
        ("I need onions and the pot must be empty and the stove ready", "cook"),
    ]
    
    for response, task_name in edge_cases:
        print(f"\n📝 Input: '{response}'")
        try:
            preconditions = rule_based_precondition_parsing(response, task_name)
            if preconditions:
                print(f"✅ Found {len(preconditions)} preconditions:")
                for fact in preconditions:
                    print(f"   - {fact}")
            else:
                print("❌ No preconditions found")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_pattern_matching():
    """Test specific regex patterns"""
    print("\n🧪 Testing Specific Regex Patterns...")
    
    # Test each pattern type individually
    pattern_tests = [
        # Resource patterns
        ("need 3 onions", "resource_check"),
        ("require at least 2 tomatoes", "resource_check"),
        ("more than 1 pot", "resource_check"),
        
        # State patterns
        ("pot must be empty", "state_check"),
        ("stove should be ready", "state_check"),
        ("kitchen is clean", "state_check"),
        
        # Boolean patterns
        ("onions available", "availability"),
        ("stove ready", "readiness"),
        ("pot empty", "emptiness"),
        
        # Negation patterns
        ("no onions", "negation"),
        ("pot not full", "negation"),
    ]
    
    for text, pattern_type in pattern_tests:
        print(f"\n📝 Testing '{text}' ({pattern_type})")
        preconditions = rule_based_precondition_parsing(text, "test")
        if preconditions:
            print(f"✅ Matched: {preconditions}")
        else:
            print("❌ No match")

def main():
    """Run all tests"""
    print("🚀 Starting Precondition Parsing Tests...\n")
    
    try:
        test_rule_based_parsing()
        test_edge_cases()
        test_pattern_matching()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
