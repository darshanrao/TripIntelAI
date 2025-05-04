# AI Travel Planner API Guide

## Base URL
```
http://localhost:8000
```

## Main Interaction Endpoint

### POST /interact
The primary endpoint for all interactions with the travel planner.

#### Request Format
```json
{
    "message": "string",              // Optional: Text input from user
    "conversation_id": "string",      // Optional: ID to maintain conversation state
    "user_id": "string",             // Optional: User identifier
    "interaction_type": "string",     // Optional: Type of interaction
    "selection_data": {              // Optional: Data for selections/feedback
        "key": "value"
    },
    "metadata": {                    // Optional: Additional context
        "key": "value"
    }
}
```

#### Interaction Types

1. **Chat Interaction** (`interaction_type: "chat"`)
```json
{
    "message": "Plan a trip to Paris for 2 people",
    "interaction_type": "chat"
}
```

2. **Flight Selection** (`interaction_type: "flight_selection"`)
```json
{
    "interaction_type": "flight_selection",
    "selection_data": {
        "flight_index": 1
    }
}
```

3. **Feedback/Modification** (`interaction_type: "feedback"`)
```json
{
    "interaction_type": "feedback",
    "selection_data": {
        "category_id": "1",
        "specific_feedback": "I prefer morning flights"
    }
}
```

#### Response Format
```json
{
    "conversation_id": "string",
    "success": true,
    "message": "string",             // Human readable response
    "data": {                        // Optional: Structured data
        "itinerary": "string",
        "trip_summary": {},
        "daily_itinerary": {},
        "flights": [],
        "selected_flight": {}
    },
    "interaction_type": "string",    // Expected next interaction
    "available_actions": [           // Possible next actions
        {
            "type": "string",
            "items": []
        }
    ],
    "error": "string"               // Optional: Error message if success is false
}
```

#### Example Responses

1. **Initial Chat Response**
```json
{
    "conversation_id": "123",
    "success": true,
    "message": "Please select your preferred flight:",
    "data": {
        "flights": [
            {
                "id": "flight1",
                "price": "$500",
                "departure": "10:00 AM",
                "arrival": "2:00 PM"
            }
        ]
    },
    "interaction_type": "flight_selection",
    "available_actions": [
        {
            "type": "selection",
            "items": [
                {
                    "id": 0,
                    "data": {"flight_details": "..."}
                }
            ]
        }
    ]
}
```

2. **Flight Selection Response**
```json
{
    "conversation_id": "123",
    "success": true,
    "message": "Flight selected! Here's your updated itinerary:",
    "data": {
        "selected_flight": {},
        "itinerary": "string",
        "trip_summary": {},
        "daily_itinerary": {}
    },
    "interaction_type": "feedback",
    "available_actions": [
        {
            "type": "modification",
            "items": [
                {
                    "id": "1",
                    "category": "Transportation",
                    "description": "Modify flights/routes"
                }
            ]
        }
    ]
}
```

## Additional Endpoints

### GET /conversations
List all active conversations.

#### Response
```json
{
    "conversations": ["id1", "id2", "id3"]
}
```

### DELETE /conversations/{conversation_id}
Delete a specific conversation.

#### Response
```json
{
    "message": "Conversation {id} deleted"
}
```

### POST /generate-itinerary
Generate a travel itinerary based on structured trip data.

#### Request
```json
{
    "metadata": {
        "destination": "string",
        "start_date": "string",
        "end_date": "string",
        "num_travelers": "integer"
    }
}
```

#### Response
```json
{
    "itinerary": "string"
}
```

### POST /voice-input
Process voice input for travel planning.

#### Request
- Form data with audio file

#### Response
Same format as /interact endpoint

### POST /save-audio
Save and process audio input with more control.

#### Request
- Form data with audio file
- Optional: keep_debug_files (boolean)

#### Response
Same format as /interact endpoint

## Error Handling

All endpoints return errors in the following format:
```json
{
    "success": false,
    "message": "Error description",
    "error": "Detailed error message"
}
```

Common HTTP status codes:
- 200: Success
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

## WebSocket Support
Coming soon: Real-time updates and notifications via WebSocket connection.

## Rate Limiting
- Default: 100 requests per minute per IP
- Voice endpoints: 20 requests per minute per IP

## Authentication
Currently using API key authentication. Include in headers:
```
Authorization: Bearer YOUR_API_KEY
```

## Best Practices
1. Always maintain conversation_id for multi-step interactions
2. Handle errors gracefully on the client side
3. Implement retry logic for network failures
4. Cache responses when appropriate
5. Follow the expected interaction flow:
   - chat → flight_selection → feedback → modifications 