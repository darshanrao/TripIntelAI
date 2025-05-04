import requests
import json

def test_mock_api():
    # API endpoint for the mock implementation
    url = "http://localhost:8001/chat"
    
    # Test query
    payload = {
        "query": "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people with focus on museums and restaurants"
    }
    
    print(f"Sending request to Mock API: {json.dumps(payload)}")
    
    # Make the API request
    try:
        response = requests.post(url, json=payload)
        
        # Print response status code
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            # Print the response
            data = response.json()
            
            if data.get("is_valid") == False:
                print("Trip validation failed:")
                for error in data.get("validation_errors", []):
                    print(f"- {error}")
            elif data.get("error"):
                print(f"Error: {data.get('error')}")
            else:
                print("\nGENERATED ITINERARY:")
                print("=" * 80)
                print(data.get("itinerary", "No itinerary generated"))
                print("=" * 80)
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_mock_api() 