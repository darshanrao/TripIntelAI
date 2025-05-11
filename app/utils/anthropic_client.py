import os
from anthropic import Anthropic
from dotenv import load_dotenv
from app.utils.logger import logger

# Load environment variables
load_dotenv()

# Initialize Anthropic client
anthropic_client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

def get_anthropic_client() -> Anthropic:
    """
    Get an instance of the Anthropic client.
    This function ensures we have a valid API key and returns a configured client.
    
    Returns:
        Anthropic: Configured Anthropic client instance
        
    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set in environment variables
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    
    return Anthropic(api_key=api_key) 