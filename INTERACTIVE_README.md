# TripIntelAI with Interactive Trip Validator

This README explains how to use the interactive trip validator component we've integrated into TripIntelAI. This feature enhances the trip planning experience by engaging users in a conversational way when information is missing or incomplete.

## Overview

The interactive trip validator:

1. Checks whether all required trip information is present
2. If information is missing, it asks the user follow-up questions
3. Processes the user's responses to complete the missing information
4. Only proceeds with trip planning once all required information is collected
5. Provides a conversational, natural experience for gathering trip details

## Files and Components

Here's what we've integrated:

- **app/nodes/trip_validator_node.py**: The enhanced validator that supports both standard validation and interactive validation with conversational functionality
- **app/nodes/enhanced_conversation_handler.py**: Handles the conversational aspects, generating natural questions
- **app/nodes/enhanced_extractor.py**: Enhanced extractors for dates, locations, and numbers
- **app/main.py**: FastAPI server that uses the interactive validation capabilities
- **run_interactive.py**: Script to run the API server

## Required Fields

The validator checks for these required fields:

- **source**: Where the trip starts from
- **destination**: Where the trip goes to
- **start_date**: When the trip begins
- **end_date**: When the trip ends
- **num_people**: How many people are traveling

## Running the API Server

To start the API server:

```bash
python run_interactive.py
```

This will start a FastAPI server on port 8002 that uses the interactive validator.

## Using the Interactive API

The interactive API works as follows:

1. Send a POST request to `/chat` with your initial query
2. If information is missing, you'll receive a response with:
   - `interactive_mode: true`
   - `next_question`: The question to ask the user
   - `conversation_id`: ID to continue the conversation
3. Send the user's answer as another POST request to `/chat` with:
   - `query`: The user's answer
   - `conversation_id`: The same ID from step 2
4. Repeat steps 2-3 until all required information is collected
5. Once all information is present, you'll receive a response with:
   - `is_valid: true`
   - `itinerary`: The generated travel itinerary

### API Request Example

Initial request:
```json
POST /chat
{
  "query": "I want to plan a trip to Hawaii"
}
```

Response:
```json
{
  "conversation_id": "abc123",
  "interactive_mode": true,
  "next_question": "I need a bit more information to plan your perfect trip. Where will you be starting your trip from?",
  "is_valid": false
}
```

Follow-up request:
```json
POST /chat
{
  "query": "New York",
  "conversation_id": "abc123"
}
```

Response:
```json
{
  "conversation_id": "abc123",
  "interactive_mode": true,
  "next_question": "I see you're planning a trip to Hawaii. When would you like to start your trip? (Please provide a date in MM/DD/YYYY format)",
  "is_valid": false
}
```

And so on until all required information is collected.

## Additional API Endpoints

- `GET /conversations`: List all active conversation IDs
- `DELETE /conversations/{conversation_id}`: Delete a conversation state
- `POST /conversations`: Create a new conversation and get an ID

## Integration with Frontend Applications

For frontend applications, you can maintain conversation state by:

1. Storing the `conversation_id` between requests
2. Displaying the `next_question` to the user
3. Sending the user's response with the same `conversation_id`
4. Continuing until you receive a complete itinerary

This approach allows for a natural conversational flow while ensuring all required trip information is collected.
