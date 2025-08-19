#!/usr/bin/env python3
"""
Quick test script for chatbot edit functionality
Tests the precondition parsing methods without needing the full VAL system
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'val'))

# Mock the necessary classes and imports
class MockFact:
    def __init__(self, name, operator, value):
        self.name = name
        self.operator = operator
        self.value = value
    
    def __str__(self):
        return f"Fact({self.name} {self.operator} {self.value})"

# Mock the Fact class
import builtins
original_import = builtins.__import__

def mock_import(name, *args, **kwargs):
    if name == 'pyhtn.conditions.fact':
        # Create a mock module
        class MockModule:
            class Fact:
                def __init__(self, name, operator, value):
                    self.name = name
                    self.operator = operator
                    self.value = value
                
                def __str__(self):
                    return f"Fact({self.name} {self.operator} {self.value})"
        
        return MockModule()
    return original_import(name, *args, **kwargs)

builtins.__import__ = mock_import

# Now import the agent
from val.agent import ValAgent

# Create a mock agent instance for testing
class MockGPTCompleter:
    def get_chat_gpt_completion(self, prompt):
        return "Mock GPT response"

class MockAgent(ValAgent):
    def __init__(self):
        # Skip the parent initialization that requires real dependencies
        self.gpt = MockGPTCompleter()
        self.precondition_parser_prompt = "Task: {task_name}\nResponse: {chatbot_response}\nParse preconditions:"

def test_rule_based_parsing():
    """Test the rule-based precondition parsing"""
    print("🧪 Testing Rule-based Precondition Parsing...")
    
    agent = MockAgent()
    
    # Test cases
    test_cases = [
        ("I need at least 3 onions to cook", "cook"),
        ("The pot must be empty before adding ingredients", "add_ingredients"),
        ("We require more than 2 tomatoes", "cook"),
        ("The stove should be ready and available", "cook"),
        ("No other ingredients should be in the pot", "cook"),
        ("The kitchen must be clean", "prepare_meal"),
    ]
    
    for response, task_name in test_cases:
        print(f"\n📝 Input: '{response}'")
        try:
            preconditions = agent._rule_based_precondition_parsing(response, task_name)
            if preconditions:
                print(f"✅ Found {len(preconditions)} preconditions:")
                for fact in preconditions:
                    print(f"   - {fact}")
            else:
                print("❌ No preconditions found")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_enhanced_nlp_parsing():
    """Test the enhanced NLP parsing (if available)"""
    print("\n🧪 Testing Enhanced NLP Parsing...")
    
    agent = MockAgent()
    
    test_cases = [
        ("I need onions to cook", "cook"),
        ("The pot is empty", "cook"),
    ]
    
    for response, task_name in test_cases:
        print(f"\n📝 Input: '{response}'")
        try:
            preconditions = agent._enhanced_nlp_parsing(response, task_name)
            if preconditions:
                print(f"✅ Found {len(preconditions)} preconditions:")
                for fact in preconditions:
                    print(f"   - {fact}")
            else:
                print("❌ No preconditions found (this is normal if NLP libraries aren't installed)")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_llm_fallback():
    """Test the LLM fallback parsing"""
    print("\n🧪 Testing LLM Fallback Parsing...")
    
    agent = MockAgent()
    
    test_cases = [
        ("Complex condition: the temperature must be between 180-200 degrees", "cook"),
        ("Special requirement: the chef must have completed safety training", "cook"),
    ]
    
    for response, task_name in test_cases:
        print(f"\n📝 Input: '{response}'")
        try:
            preconditions = agent._llm_based_precondition_parsing(response, task_name)
            if preconditions:
                print(f"✅ Found {len(preconditions)} preconditions:")
                for fact in preconditions:
                    print(f"   - {fact}")
            else:
                print("❌ No preconditions found (this is normal with mock GPT)")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_full_parse_preconditions():
    """Test the complete parse_preconditions method"""
    print("\n🧪 Testing Complete parse_preconditions Method...")
    
    agent = MockAgent()
    
    test_cases = [
        ("I need 2 onions and the pot must be empty", "cook"),
        ("The stove should be ready and we need at least 1 tomato", "prepare_meal"),
        ("Complex: temperature between 180-200°C, chef certified, kitchen clean", "cook"),
    ]
    
    for response, task_name in test_cases:
        print(f"\n📝 Input: '{response}'")
        try:
            preconditions = agent.parse_preconditions(response, task_name)
            if preconditions:
                print(f"✅ Found {len(preconditions)} preconditions:")
                for fact in preconditions:
                    print(f"   - {fact}")
            else:
                print("❌ No preconditions found")
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting Chatbot Edit Functionality Tests...\n")
    
    try:
        test_rule_based_parsing()
        test_enhanced_nlp_parsing()
        test_llm_fallback()
        test_full_parse_preconditions()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
