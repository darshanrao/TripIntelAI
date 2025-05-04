# TripIntelAI with ReAct Framework

This enhanced version of TripIntelAI integrates the ReAct (Reasoning + Acting) framework to provide a more natural, conversational travel planning experience. By combining Claude AI's language capabilities with a structured planning approach, the system can understand natural language, make decisions when users are flexible, and maintain a coherent conversation throughout the planning process.

## Key Features

- **Natural Language Understanding**: Process inputs like "sometime in July" or "a family of four" without requiring exact formats
- **Flexible Response Handling**: When users say "anything is fine" or "you decide," the system makes intelligent suggestions
- **Conversational Flow**: Varied, personalized responses that reference previous information
- **Autonomous Decision-Making**: Makes reasonable choices when users are flexible about travel details
- **Comprehensive Planning**: Creates personalized travel plans based on conversational inputs

## Components

### 1. Enhanced Extractors

Located in `app/nodes/enhanced_extractor.py`, these modules use Claude AI to extract structured data from natural language:

- `enhanced_date_extraction`: Understands various date formats and expressions
- `enhanced_number_extraction`: Processes natural language number expressions
- `enhanced_location_extraction`: Handles location references and normalizes them

### 2. Conversation Handler

Located in `app/nodes/enhanced_conversation_handler.py`, this component:

- Generates varied, natural-sounding questions
- Maintains conversation history
- Handles flexible responses with intelligent decision-making
- Provides contextual acknowledgments and transitions

### 3. Combined Trip Validator

Located in `app/nodes/trip_validator_node.py`, this validator:

- Supports both standard validation and interactive validation modes
- Uses the enhanced conversation handler for natural dialogs in interactive mode
- Combines reasoning steps with concrete actions
- Integrates flexible response handling
- Validates trip information in a conversational way
- Fully compatible with both standard and interactive workflows

## How It Works

1. The system takes an initial travel query from the user
2. It extracts as much structured information as possible
3. It identifies missing required fields
4. In interactive mode, it enters a conversational loop, asking for additional information
5. When users provide flexible responses, it makes intelligent suggestions
6. Once all required information is gathered, it validates the trip details
7. Finally, it allows the planning process to continue with complete information

## Running the Tests

### Enhanced Validator Test

```bash
python test_enhanced.py
```

This will let you:
- Test the enhanced conversational validator
- Test handling of flexible responses
- Compare basic vs enhanced extraction capabilities

## Requirements

- Python 3.8+
- Anthropic API key (set as ANTHROPIC_API_KEY in your environment or .env file)
- Required packages listed in requirements.txt

## Installation

```bash
pip install -r requirements.txt
```

Create a `.env` file with your API keys:

```
ANTHROPIC_API_KEY=your_api_key_here
GOOGLE_PLACES_API_KEY=your_api_key_here
```

## Integrating Into Your Application

To use the trip validator in your application:

```python
from app.nodes.trip_validator_node import trip_validator_node, process_user_response

# Create initial state
state = {
    "query": "I want to visit Miami",
    "metadata": type('obj', (object,), {
        "source": None,
        "destination": None,
        "start_date": None,
        "end_date": None,
        "num_people": None,
        "preferences": None
    }),
    "interactive_mode": True  # Enable interactive capabilities
}

# Process initial query
state = await trip_validator_node(state)

# Handle user responses in a conversation
while state.get("interactive_mode") and state.get("missing_fields"):
    # Display question to user
    print(state["next_question"])
    
    # Get user response
    user_input = input("> ")
    
    # Process response
    state = await process_user_response(state, user_input)

# When complete, trip details are in state["metadata"]
if state["is_valid"]:
    print(f"Trip from {state['metadata'].source} to {state['metadata'].destination}")
``` 