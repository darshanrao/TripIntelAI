import asyncio
from app.graph.trip_planner_graph import TripPlannerGraph
from app.utils.logger import logger

async def test_graph():
    """Test the TripPlannerGraph with various scenarios."""
    planner = TripPlannerGraph()
    
    # Test cases with different levels of detail
    test_queries = [
        # Minimal query - should trigger missing info handler
        "I want to go to Japan",
        
        # Complete query with all details
        "Plan a trip from New York to London from July 1 to July 10, 2024 for 2 people",
        
        # Query with some missing details
        "I need a vacation in Tokyo next month for 3 people",
        
        # Query with specific preferences
        "Plan a family trip to Paris in summer for 5 days, focusing on museums and local cuisine"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test Case {i}: {query}")
        print("=" * 80)
        
        try:
            # Process the query
            print("\n🤔 Processing query...")
            result = await planner.process(query)
            
            # Print validation status
            print(f"\nValidation status: {'✅ Valid' if result.get('is_valid', False) else '❌ Invalid'}")
            
            # Print validation errors if any
            if not result.get("is_valid", False):
                print("\nValidation errors:")
                for error in result.get("validation_errors", []):
                    print(f"  - {error}")
            
            # Print metadata
            if "metadata" in result:
                print("\nExtracted metadata:")
                for key, value in result["metadata"].items():
                    print(f"  {key}: {value}")
            
            # Print nodes that were called
            if "nodes_to_call" in result:
                print("\nNodes called in sequence:")
                for node in result["nodes_to_call"]:
                    print(f"  - {node}")
            
            # Print flight data if available
            if "flight_data" in result and result["flight_data"]:
                print("\nFlight options:")
                for flight in result["flight_data"]:
                    print(f"  - {flight.get('airline', 'Unknown')} from {flight.get('source', 'Unknown')} to {flight.get('destination', 'Unknown')}")
            
            # Print hotel data if available
            if "hotel_data" in result and result["hotel_data"]:
                print("\nHotel options:")
                print(f"  - {result['hotel_data'].get('name', 'Unknown')} in {result['hotel_data'].get('location', 'Unknown')}")
            
            # Print itinerary if available
            if "itinerary" in result:
                print("\nGenerated itinerary:")
                print(result["itinerary"])
            
            print("\n" + "=" * 80)
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {str(e)}")
            print(f"❌ Error: {str(e)}")
            print("=" * 80)

if __name__ == "__main__":
    print("\n🚀 Starting TripPlannerGraph Tests")
    print("=" * 80)
    asyncio.run(test_graph()) 