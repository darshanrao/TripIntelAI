import os
import requests
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def test_perplexity_api():
    # Get API key from environment
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY is not set in the environment.")
    
    # Clean up the API key
    api_key = api_key.strip().strip('"\'')
    logger.info(f"Using API key: {api_key[:8]}...")
    
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
    
    logger.info("Sending test request to Perplexity API...")
    logger.info(f"URL: {url}")
    logger.info(f"Headers: {headers}")
    logger.info(f"Payload: {payload}")
    
    try:
        # Make the API request
        response = requests.post(url, json=payload, headers=headers)
        
        # Print the response
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {response.text}")
        
        # Check if the request was successful
        assert response.status_code == 200, f"API request failed with status code {response.status_code}: {response.text}"
        
        # Try to parse the response as JSON
        try:
            result = response.json()
            logger.info("Successfully parsed JSON response")
            return result
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    test_perplexity_api() 