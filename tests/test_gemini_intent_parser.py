import asyncio
import os
import pytest
from dotenv import load_dotenv
from app.nodes.intent_parser_node import intent_parser_node

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_intent_parser():
    """Test the intent parser with various queries."""
    test_cases = [
        {
            "query": "I want to go to Paris from New York for 5 days starting May 15th, 2024. I'm interested in museums and food.",
            "expected_fields": ["source", "destination", "start_date", "end_date", "num_people", "preferences"]
        },
        {
            "query": "Planning a family trip to Tokyo next summer. We'll be 4 people.",
            "expected_fields": ["destination", "num_people"]
        },
        {
            "query": "Looking for a romantic getaway to Bali in December",
            "expected_fields": ["destination", "preferences"]
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting query: {test_case['query']}")
        state = {"query": test_case["query"]}
        
        try:
            result = await intent_parser_node(state)
            print(f"Result: {result}")
            
            if result.get("is_valid"):
                metadata = result.get("metadata", {})
                print("Extracted metadata:")
                for field in test_case["expected_fields"]:
                    print(f"- {field}: {metadata.get(field)}")
            else:
                print(f"Error: {result.get('error')}")
                
        except Exception as e:
            print(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_intent_parser()) 