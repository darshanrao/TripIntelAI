import asyncio
from app.graph.trip_planner_graph import TripPlannerGraph
from app.utils.logger import logger

async def test_trip_planner():
    """Test the trip planner with a simple travel query."""
    print("\n=== Testing Trip Planner ===")
    
    # Create graph instance
    graph = TripPlannerGraph()
    
    # Test query
    query = "I want to plan a trip to Paris for 2 people to May 20, 2024"
    print(f"\nTest Query: {query}")
    
    # Initialize state
    state = {
        "query": query,
        "metadata": {},
        "is_valid": False,
        "next_question": None,
        "error": None,
        "thought": None,
        "action": None,
        "action_input": None,
        "observation": None
    }
    
    try:
        # Process the query
        print("\nProcessing query...")
        result = await graph.process(state)
        
        # Print results
        print("\nResults:")
        print("-" * 50)
        print(f"Valid: {result.get('is_valid', False)}")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        
        if result.get('next_question'):
            print(f"Next Question: {result['next_question']}")
        
        if result.get('metadata'):
            print("\nExtracted Metadata:")
            metadata = result['metadata']
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    print(f"- {key}: {value}")
            else:
                # Handle TripMetadata object
                metadata_dict = metadata.dict()
                for key, value in metadata_dict.items():
                    print(f"- {key}: {value}")
        
        if result.get('thought'):
            print(f"\nThought: {result['thought']}")
        
        if result.get('action'):
            print(f"Action: {result['action']}")
            if result.get('action_input'):
                print(f"Action Input: {result['action_input']}")
        
        print("-" * 50)
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        print(f"\nError occurred: {str(e)}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_trip_planner()) 