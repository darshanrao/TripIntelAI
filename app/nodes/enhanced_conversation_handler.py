import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from anthropic import Anthropic

import dotenv
dotenv.load_dotenv()
# Initialize Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class ConversationHandler:
    """
    Enhanced conversation handler using ReAct to make the assistant more dynamic and conversational.
    Handles natural language understanding and generation for the travel planning process.
    """
    
    def __init__(self):
        self.conversation_history = []
        self.response_variety = {
            "greetings": [
                "Hi there! I'd love to help plan your trip.",
                "Hello! I'm excited to help you with your travel plans.",
                "Welcome! Let's plan an amazing trip together."
            ],
            "acknowledgments": [
                "Great! That's helpful information.",
                "Perfect! I've got that noted down.",
                "Excellent choice!"
            ],
            "transitions": [
                "Now, I need to know a bit more about your plans.",
                "Let's move on to the next part of your trip.",
                "To continue planning your perfect trip,"
            ]
        }
    
    def add_to_history(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    async def generate_question(self, missing_field: str, metadata, previous_fields: List[str] = None) -> str:
        """
        Generate a conversational question for a missing field using ReAct framework.
        
        Args:
            missing_field: The field we need information about
            metadata: Current trip metadata
            previous_fields: Fields we've already asked about
            
        Returns:
            A natural-sounding question to ask the user
        """
        # Prepare context for Claude
        context = {
            "missing_field": missing_field,
            "known_info": {k: v for k, v in metadata.__dict__.items() if v is not None},
            "previous_fields": previous_fields or []
        }
        
        field_descriptions = {
            "source": "where they're starting their trip from",
            "destination": "where they'd like to go",
            "start_date": "when they want to start their trip",
            "end_date": "when they want to end their trip",
            "num_people": "how many people will be traveling",
            "preferences": "what activities or preferences they have for the trip"
        }
        
        # Build the ReAct prompt
        prompt = f"""
        <task>
        Generate a natural, conversational question to ask a user about their travel plans.
        
        Context:
        - We need to ask about: {field_descriptions.get(missing_field, missing_field)}
        - Known information: {json.dumps(context["known_info"])}
        - Previous topics discussed: {', '.join(context["previous_fields"]) if context["previous_fields"] else "None yet"}
        
        First, think about:
        1. How to reference existing information naturally
        2. How to vary the phrasing from standard templates
        3. How to make the question engaging and friendly
        
        Then, generate a conversational question that doesn't sound repetitive or robotic.
        Make sure your response is a single question/statement, not a full conversation.
        </task>
        """
        
        # Call Claude with ReAct framework
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=150,
            temperature=0.7,  # Slightly higher temperature for more variety
            system="You are a friendly, conversational travel assistant helping someone plan their trip.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract the generated question
        question = response.content[0].text.strip()
        
        # Clean up any extraneous text like "Here's my question:" that Claude might include
        prefixes_to_remove = ["Here's my question:", "My question:", "I would ask:", "Question:"]
        for prefix in prefixes_to_remove:
            if question.startswith(prefix):
                question = question[len(prefix):].strip()
        
        return question
    
    async def handle_flexible_response(self, field: str, user_response: str, metadata) -> Dict[str, Any]:
        """
        Handle responses where the user is flexible ("anything is fine", "you decide", etc.)
        
        Args:
            field: The field the user is flexible about
            user_response: What the user said
            metadata: Current trip metadata
            
        Returns:
            Dict with suggested value and explanation
        """
        # Prepare context
        context = {
            "field": field,
            "user_response": user_response,
            "known_info": {k: v for k, v in metadata.__dict__.items() if v is not None},
            "current_date": datetime.now().isoformat()
        }
        
        # Build the ReAct prompt
        prompt = f"""
        <task>
        The user is planning a trip and has indicated flexibility about {field}, saying: "{user_response}"
        
        Current information about their trip: {json.dumps(context["known_info"])}
        Today's date: {context["current_date"]}
        
        First, determine:
        1. Is the user truly being flexible, or just unclear?
        2. What would be a reasonable suggestion based on travel best practices?
        3. What constraints exist based on the other trip details?
        
        Then, make a specific suggestion that's reasonable and explain your reasoning.
        Provide your response as a JSON object with:
        - "is_flexible": true/false - whether user is actually being flexible
        - "suggested_value": your specific suggestion
        - "explanation": brief explanation of why you chose this
        </task>
        """
        
        # Call Claude with ReAct framework
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=300,
            temperature=0,
            system="You are a travel planning expert making reasonable suggestions based on best practices.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract the reasoning and suggested value
        reasoning = response.content[0].text
        
        # Try to extract JSON from the response
        try:
            # Find JSON-like content between curly braces
            import re
            json_match = re.search(r'\{.*\}', reasoning, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return result
            else:
                # Fallback if JSON parsing fails
                return {
                    "is_flexible": True,
                    "suggested_value": self._get_default_for_field(field, metadata),
                    "explanation": "I've selected a standard option that works for most travelers."
                }
        except Exception as e:
            print(f"Error parsing flexibility response: {e}")
            return {
                "is_flexible": True,
                "suggested_value": self._get_default_for_field(field, metadata),
                "explanation": "I've selected a reasonable option based on your other trip details."
            }
    
    def _get_default_for_field(self, field: str, metadata) -> Any:
        """Get a reasonable default value for a field when user is flexible."""
        today = datetime.now()
        
        if field == "start_date":
            # Default to 4 weeks from now (common planning horizon)
            future = today + timedelta(days=28)
            return future.strftime("%m/%d/%Y")
            
        elif field == "end_date":
            # If we have a start date, default to 1 week after
            if hasattr(metadata, "start_date") and metadata.start_date:
                try:
                    start = datetime.strptime(metadata.start_date, "%m/%d/%Y")
                    end = start + timedelta(days=7)
                    return end.strftime("%m/%d/%Y")
                except:
                    pass
            # Otherwise 5 weeks from now
            future = today + timedelta(days=35)
            return future.strftime("%m/%d/%Y")
            
        elif field == "num_people":
            return 2  # Default to 2 people
            
        elif field == "preferences":
            return ["sightseeing", "local cuisine"]  # Common preferences
            
        return None

    async def is_flexible_response(self, user_input: str) -> bool:
        """
        Determine if the user's response indicates flexibility or indifference.
        
        Args:
            user_input: The user's response text
            
        Returns:
            Boolean indicating if the response suggests flexibility
        """
        flexible_phrases = [
            "anything", "whatever", "you decide", "you choose", "doesn't matter",
            "don't care", "not sure", "flexible", "any", "open to suggestions"
        ]
        
        # Simple check for flexible phrases
        lower_input = user_input.lower()
        for phrase in flexible_phrases:
            if phrase in lower_input:
                return True
                
        # For more complex cases, use Claude
        prompt = f"""
        <task>
        Determine if this user response indicates flexibility or indifference: "{user_input}"
        
        Think about:
        1. Does the user explicitly say they're flexible?
        2. Does the user imply they don't have a preference?
        3. Is the user asking for a suggestion or recommendation?
        
        Answer only with "YES" if the response indicates flexibility, or "NO" if it doesn't.
        </task>
        """
        
        try:
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=50,
                temperature=0,
                system="You analyze if text indicates flexibility or indifference.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            answer = response.content[0].text.strip().upper()
            return "YES" in answer
        except:
            # Fallback to basic check if Claude call fails
            return any(p in lower_input for p in ["suggest", "recommend", "what do you", "what would you"]) 