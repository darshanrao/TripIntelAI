import requests
import json
import time
import argparse

def test_api_endpoint(query, url="http://localhost:8000/chat", verbose=False):
    """
    Test the TripIntelAI API endpoint by sending a query and getting a response.
    
    Args:
        query (str): The travel query to process
        url (str): The API endpoint URL
        verbose (bool): Whether to print verbose output
    
    Returns:
        dict: The response from the API
    """
    # Prepare the request payload
    payload = {
        "query": query
    }
    
    if verbose:
        print(f"Sending query to {url}:")
        print(f"  Query: {query}")
        print("Waiting for response...")
    
    # Start timing
    start_time = time.time()
    
    try:
        # Send the request
        response = requests.post(url, json=payload)
        
        # End timing
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            
            if verbose:
                print(f"Response received in {elapsed_time:.2f} seconds")
                print(f"Status code: {response.status_code}")
            
            # Check if the response contains an itinerary
            if result.get("itinerary"):
                print("\n✨ ITINERARY RECEIVED ✨")
                print("=" * 80)
                print(result["itinerary"])
                print("=" * 80)
                print(f"Response time: {elapsed_time:.2f} seconds")
                return result
            
            # Check if there was a validation error
            elif not result.get("is_valid", True):
                print("\n❌ VALIDATION ERROR")
                for error in result.get("validation_errors", []):
                    print(f"  - {error}")
                return result
            
            # Other error
            else:
                print("\n❌ RESPONSE ERROR")
                print(f"  Error: {result.get('error', 'Unknown error')}")
                return result
        
        else:
            print(f"\n❌ REQUEST FAILED: Status code {response.status_code}")
            print(response.text)
            return {"error": f"Request failed with status code {response.status_code}"}
    
    except Exception as e:
        print(f"\n❌ EXCEPTION: {str(e)}")
        return {"error": str(e)}

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Test the TripIntelAI API endpoint")
    parser.add_argument("--query", "-q", type=str, 
                        default="I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people with focus on museums and good restaurants",
                        help="The travel query to process")
    parser.add_argument("--url", "-u", type=str, 
                        default="http://localhost:8000/chat",
                        help="The API endpoint URL")
    parser.add_argument("--mock", "-m", action="store_true",
                        help="Use the mock API endpoint on port 8001")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print verbose output")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Use mock URL if specified
    if args.mock:
        args.url = "http://localhost:8001/chat"
    
    # Print header
    print("=" * 80)
    print("🌍 TripIntelAI API Testing Tool 🌍")
    print("=" * 80)
    print(f"Testing API endpoint: {args.url}")
    print(f"Query: {args.query}")
    print("-" * 80)
    
    # Test the API endpoint
    test_api_endpoint(args.query, args.url, args.verbose)

if __name__ == "__main__":
    main() 