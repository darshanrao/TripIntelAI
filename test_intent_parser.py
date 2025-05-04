import asyncio
import logging
import json
import sys
from app.nodes.intent_parser_node import intent_parser_node

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_intent_parser(query):
    """Test the intent parser with a specific query"""
    logger.info(f"\n\n====== Testing Intent Parser with: '{query}' ======")
    
    # Create state with query
    state = {"raw_query": query}
    
    # Call the intent parser
    try:
        result_state = await intent_parser_node(state)
        
        # Check for errors
        if "error" in result_state and result_state["error"]:
            logger.error(f"Parser returned error: {result_state['error']}")
            return False
        
        # Check if metadata was extracted
        if "metadata" not in result_state or not result_state["metadata"]:
            logger.error("No metadata was extracted")
            return False
        
        # Print the extracted metadata
        metadata = result_state["metadata"]
        logger.info("Successfully extracted metadata:")
        metadata_dict = {
            "source": str(metadata.source),
            "destination": str(metadata.destination),
            "start_date": str(metadata.start_date),
            "end_date": str(metadata.end_date),
            "num_people": metadata.num_people,
            "preferences": metadata.preferences
        }
        logger.info(json.dumps(metadata_dict, indent=2))
        return True
        
    except Exception as e:
        logger.error(f"Exception during intent parsing: {str(e)}")
        return False

async def run_tests():
    """Run a series of tests with different inputs"""
    test_queries = [
        "I want to go to Boston",
        "I want to go to Boston from NYC",
        "I want to go to Boston from NYC on May 15",
        "I want to go to Boston from NYC from May 15 to May 18",
        "I want to go to Boston from NYC from May 15 to May 18 for 2 people",
        "i want to go to bsoton from may 18th to mmay 21th 2025 for 2 people",  # with typos
        "trip to Paris in the summer with my family",
        "NYC to LA next week for business"
    ]
    
    results = []
    for query in test_queries:
        success = await test_intent_parser(query)
        results.append((query, success))
    
    # Print summary
    logger.info("\n\n====== Test Summary ======")
    for query, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status}: {query}")

if __name__ == "__main__":
    # Allow custom test input from command line
    if len(sys.argv) > 1:
        # Join all arguments as a single query
        test_query = " ".join(sys.argv[1:])
        asyncio.run(test_intent_parser(test_query))
    else:
        # Run all tests
        asyncio.run(run_tests()) 