import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_perplexity_api():
    # Get API key from environment
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY is not set in the environment.")
    
    # API endpoint
    url = "https://api.perplexity.ai/chat/completions"
    
    # Test payload
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise."
            },
            {
                "role": "user",
                "content": "Find 2 flights from San Francisco to New York on 2024-05-20. For each flight, provide: airline name, flight number, departure airport code and city, arrival airport code and city, departure and arrival times, price in USD, duration in minutes, number of stops, aircraft type, cabin class, and whether baggage is included. Format the response as a JSON array of flight objects."
            }
        ]
    }
    
    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Make the API request
    response = requests.post(url, json=payload, headers=headers)
    
    # Print the response
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Check if the request was successful
    assert response.status_code == 200, f"API request failed with status code {response.status_code}: {response.text}"

if __name__ == "__main__":
    test_perplexity_api() 