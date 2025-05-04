import asyncio
from mock_intent_parser import mock_intent_parser

async def test_mock_parser():
    # Test query
    query = "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people with focus on museums and good restaurants"
    
    print(f"Testing mock parser with query: {query}")
    
    # Create initial state
    state = {
        "raw_query": query,
        "error": None
    }
    
    # Call the mock parser
    result = await mock_intent_parser(state)
    
    # Print the extracted metadata
    print("\nEXTRACTED METADATA:")
    print("=" * 80)
    metadata = result.get("metadata")
    if metadata:
        print(f"Source: {metadata.source}")
        print(f"Destination: {metadata.destination}")
        print(f"Start date: {metadata.start_date}")
        print(f"End date: {metadata.end_date}")
        print(f"Number of people: {metadata.num_people}")
        print(f"Preferences: {metadata.preferences}")
    else:
        print("No metadata extracted")
        print(f"Error: {result.get('error')}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_mock_parser()) 