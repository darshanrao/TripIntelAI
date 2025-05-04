import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from anthropic import Anthropic

# Initialize Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

async def enhanced_date_extraction(user_input: str, field_name: str, context: dict = None) -> Optional[str]:
    """
    Use Claude to extract and normalize date information from user input
    using the ReAct framework (Reasoning + Acting)
    
    Args:
        user_input: The user's natural language response
        field_name: Which date field we're extracting (start_date or end_date)
        context: Additional context from the conversation
        
    Returns:
        Normalized date string in MM/DD/YYYY format or None if can't be parsed
    """
    try:
        # Build the prompt with reasoning steps
        current_year = datetime.now().year
        today = datetime.now()
        
        # Construct conversation context
        destination = context.get('destination', 'their destination') if context else 'their destination'
        
        prompt = f"""
        <task>
        Extract a valid travel date from the following user input: "{user_input}".
        This is for the {field_name} of a trip to {destination}.
        
        Today's date is {today.strftime('%B %d, %Y')}.
        Format the output date as MM/DD/YYYY.
        
        First, think step by step:
        1. What date information is in the input?
        2. Is the month specified? If so, convert month names to numbers.
        3. Is the day specified?
        4. Is the year specified? If not, assume it's {current_year} if in the future, or {current_year+1} if the date has already passed this year.
        5. Check if the resulting date is valid and in the future.
        6. Format as MM/DD/YYYY.
        
        If you can't extract a valid date, explain why.
        Then provide your final answer ONLY in MM/DD/YYYY format if a valid date was found, or write "INVALID_DATE" if no valid date could be extracted.
        </task>
        """
        
        # Call Claude with ReAct framework
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=300,
            temperature=0,
            system="You are a helpful assistant specialized in understanding date information for travel planning.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract the reasoning and answer
        reasoning = response.content[0].text
        
        # Parse the MM/DD/YYYY date from the response
        date_pattern = r'\b(0?[1-9]|1[0-2])/(0?[1-9]|[12][0-9]|3[01])/(\d{4})\b'
        date_match = re.search(date_pattern, reasoning)
        
        if date_match:
            month, day, year = date_match.groups()
            return f"{int(month):02d}/{int(day):02d}/{year}"
        
        # Check if the response contained an explicit invalid date marker
        if "INVALID_DATE" in reasoning:
            return None
            
        # Try to find any date-like pattern as a fallback
        any_date_pattern = r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})'
        any_date_match = re.search(any_date_pattern, reasoning)
        if any_date_match:
            month, day, year = any_date_match.groups()
            return f"{int(month):02d}/{int(day):02d}/{year}"
            
        return None
    
    except Exception as e:
        print(f"Error using Claude for date extraction: {str(e)}")
        return None

async def enhanced_number_extraction(user_input: str) -> Optional[int]:
    """
    Use Claude to extract a number from user input, handling various formats and expressions.
    
    Args:
        user_input: The user's natural language response
        
    Returns:
        Extracted number as an integer, or None if no valid number found
    """
    try:
        prompt = f"""
        <task>
        Extract a valid number of travelers from the following user input: "{user_input}".
        
        First, think step by step:
        1. Is there a numeric digit in the input? (e.g., "2", "10")
        2. Is there a written number word? (e.g., "two", "ten")
        3. Is there a descriptive phrase that implies a number? (e.g., "a couple" = 2, "a family of four" = 4)
        4. Make sure the number makes sense for travelers (generally between 1-20 people).
        
        If you can't extract a valid number, explain why.
        Then provide your final answer ONLY as a digit if a valid number was found, or write "INVALID_NUMBER" if no valid number could be extracted.
        </task>
        """
        
        # Call Claude with ReAct framework
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=300,
            temperature=0,
            system="You are a helpful assistant specialized in understanding travel information.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract the reasoning and answer
        reasoning = response.content[0].text
        
        # Parse a number from the response
        number_pattern = r'\b(\d+)\b'
        number_match = re.search(number_pattern, reasoning)
        
        if number_match:
            return int(number_match.group(1))
        
        # Check if the response contained an explicit invalid number marker
        if "INVALID_NUMBER" in reasoning:
            return None
            
        return None
    
    except Exception as e:
        print(f"Error using Claude for number extraction: {str(e)}")
        return None

async def enhanced_location_extraction(user_input: str, field_name: str) -> Optional[str]:
    """
    Use Claude to extract and normalize location information from user input.
    
    Args:
        user_input: The user's natural language response
        field_name: Which location field we're extracting (source or destination)
        
    Returns:
        Normalized location name or None if can't be parsed
    """
    try:
        prompt = f"""
        <task>
        Extract a valid location name for travel from the following user input: "{user_input}".
        This is for the {field_name} of a trip.
        
        First, think step by step:
        1. What location information is in the input?
        2. Is it a city, country, region, or landmark?
        3. Format the location name properly with correct capitalization.
        4. If multiple locations are mentioned, identify the most likely {field_name} location.
        
        If you can't extract a valid location, explain why.
        Then provide your final answer ONLY as the location name if valid, or write "INVALID_LOCATION" if no valid location could be extracted.
        </task>
        """
        
        # Call Claude with ReAct framework
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=300,
            temperature=0,
            system="You are a helpful assistant specialized in understanding travel information.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract the reasoning and answer
        full_response = response.content[0].text
        
        # Try to find the answer at the end of the text
        lines = full_response.strip().split('\n')
        answer_line = lines[-1].strip()
        
        # If the last line isn't "INVALID_LOCATION" and isn't too complex, use it
        if "INVALID_LOCATION" not in answer_line and len(answer_line.split()) <= 5:
            return answer_line
            
        # Try to find any quoted location as a fallback
        quoted_pattern = r'"([^"]+)"'
        quoted_match = re.search(quoted_pattern, full_response)
        if quoted_match:
            return quoted_match.group(1)
        
        # If we have a short response overall, use it
        if len(full_response.strip()) < 50 and "INVALID" not in full_response:
            return full_response.strip()
            
        return None
    
    except Exception as e:
        print(f"Error using Claude for location extraction: {str(e)}")
        return None 