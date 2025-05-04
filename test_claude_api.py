from anthropic import Anthropic
import asyncio
import logging
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_claude_json_direct():
    """Test Claude API directly to get JSON response"""
    # Initialize Anthropic API client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables")
        return
    
    client = Anthropic(api_key=api_key)
    
    # Create a simple prompt
    prompt = """Extract travel information from this query: "I want to go to Boston"

Please return your answer in JSON format with these fields:
- source (string or null)
- destination (string)
- start_date (YYYY-MM-DD string or null)
- end_date (YYYY-MM-DD string or null)
- num_people (integer, default 1)
- preferences (array of strings)
"""
    
    try:
        # Make API call
        logger.info("Calling Claude API directly")
        
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            temperature=0,
            system="You extract travel information and return it as valid JSON.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Get response content
        content = response.content[0].text
        logger.info(f"Received raw response: {content}")
        
        # Try to extract JSON
        try:
            # Find JSON object
            import re
            json_match = re.search(r'(\{.*\})', content, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                logger.info(f"Found JSON in response: {json_str}")
                result = json.loads(json_str)
                logger.info(f"Parsed JSON: {json.dumps(result, indent=2)}")
                return result
            else:
                logger.error("No JSON object found in response")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        return None

# Run the test function
if __name__ == "__main__":
    result = asyncio.run(test_claude_json_direct())
    if result:
        print("TEST PASSED: Successfully got JSON response")
    else:
        print("TEST FAILED: Could not get valid JSON response") 