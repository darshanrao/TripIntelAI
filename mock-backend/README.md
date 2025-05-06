# TripIntelAI Mock Backend

This is a simple mock backend for testing the TripIntelAI frontend. It provides dummy endpoints for chat, flight search, and itinerary generation.

## Setup

```bash
# Install dependencies
npm install

# Start the server
npm start

# Or start with automatic restart on file changes
npm run dev
```

## Endpoints

The mock backend provides the following endpoints:

- `GET /health` - Health check
- `POST /conversations` - Create a new conversation
- `GET /conversations/:id` - Get conversation history
- `POST /chat` - Send a chat message
- `POST /search-flights` - Search for flights
- `POST /generate-itinerary` - Generate an itinerary
- `POST /select-flight` - Select a flight
- `POST /voice-input` - Process voice input

## Testing with the Frontend

To test the frontend with this mock backend:

1. Start the mock backend with `npm run dev`
2. Configure the frontend to use the mock backend by setting `USE_MOCK_API = true` in `services/config.js`
3. Start the frontend with `npm run dev`
4. Navigate to the frontend in your browser (typically at http://localhost:3000)

## Mock Data

The mock backend provides predefined dummy data for:

- Chat responses based on message keywords
- Flight search results
- Itinerary data with activities, accommodations, etc.

You can modify the mock data in `mockData.js` to suit your testing needs.

## Simulated Latency

The mock API includes simulated network latency to better mimic a real-world scenario. This helps in testing loading states and UI responsiveness.

## Limitations

- This is a simple REST API mock - WebSockets are acknowledged but not fully implemented
- All data is stored in memory and will be lost when the server restarts
- File uploads (like audio files) are not actually processed - random responses are provided 