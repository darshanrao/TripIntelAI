from google.generativeai import GenerativeModel, configure
import google.api_core.exceptions
import time
import os
from dotenv import load_dotenv
from app.utils.logger import logger
import asyncio
from typing import Optional

# Load environment variables
load_dotenv()

def get_gemini_client(model_name="gemini-2.0-flash"):
    """
    Get a configured Gemini client instance.
    
    Args:
        model_name (str): The Gemini model to use
        
    Returns:
        GenerativeModel: Configured Gemini model instance
        
    Raises:
        ValueError: If GEMINI_API_KEY is not set in environment variables
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    
    # Configure the API
    configure(api_key=api_key)
    
    # Initialize and return the model
    return GenerativeModel(model_name)

async def get_gemini_response(
    prompt: str,
    model: str = "gemini-2.0-flash",
    max_tokens: int = 1000,
    retries: int = 3
) -> Optional[str]:
    """
    Get a response from the Gemini API with retry logic.
    
    Args:
        prompt: The prompt to send to the model
        model: The model to use (default: gemini-2.0-flash)
        max_tokens: Maximum number of tokens in the response
        retries: Number of retries for rate limiting
        
    Returns:
        The model's response text or None if all retries failed
    """
    for attempt in range(retries):
        try:
            # Initialize the model
            model = GenerativeModel(model)
            
            # Generate response
            response = model.generate_content(prompt)
            
            # Extract the text from the response
            return response.text
            
        except Exception as e:
            error_message = str(e)
            print(f"API error: {error_message}")
            
            # Check if it's a rate limit error
            if "rate limit" in error_message.lower() and attempt < retries - 1:
                # Exponential backoff
                wait_time = (2 ** attempt) * 1
                print(f"Rate limited. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
                
            # If it's the last attempt, raise the error
            if attempt == retries - 1:
                raise Exception(f"Failed to get response from Gemini after {retries} attempts")
            
    return None 