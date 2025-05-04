# AI Travel Planner

An AI-powered travel planning application using LangGraph, Claude, and FastAPI.

## Overview

This application uses a LangGraph pipeline to create travel itineraries based on natural language queries. The pipeline consists of several nodes that handle different aspects of the travel planning process:

1. **ChatInputNode**: Accepts natural language input
2. **IntentParserNode**: Extracts structured travel intent from user input
3. **TripValidatorNode**: Validates trip parameters
4. **PlannerNode**: Decides which agent nodes to call
5. **Agent Nodes**:
   - **FlightsNode**: Finds flight options
   - **RouteNode**: Calculates route information
   - **PlacesNode**: Finds attractions using Google Places API
   - **RestaurantsNode**: Finds dining options using Google Places API
   - **HotelNode**: Finds accommodation using Google Places API
   - **BudgetNode**: Calculates budget estimates
6. **SummaryNode**: Generates a natural language itinerary

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-travel-planner.git
cd ai-travel-planner
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:
```
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_PLACES_API_KEY=your_google_places_api_key
# Add other API keys as needed (Amadeus, etc.)
```

### API Keys
- **Anthropic API Key**: Get one from the [Anthropic Console](https://console.anthropic.com/)
- **Google Places API Key**: Get one from the [Google Cloud Console](https://console.cloud.google.com/) with the Places API enabled

## Running the Application

Run the application with:
```bash
python run.py
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### Chat-based Query
```
POST /chat
```
Request body:
```json
{
  "query": "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people."
}
```

### Direct Itinerary Generation
```
POST /generate-itinerary
```
Request body with structured trip data.

## Example Usage

```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={"query": "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people."}
)

print(response.json())
```

## Features

- Natural language processing with Claude
- Dynamic workflow using LangGraph
- Real attractions, restaurants, and hotels using Google Places API
- Comprehensive budget estimation
- Customized recommendations based on user preferences

## Current Limitations

- Flight data uses mock data instead of a real API (like Amadeus)
- Limited error handling
- No persistent memory for multi-turn conversations

## Future Improvements

- Integration with a flight booking API
- Adding a conversational memory store
- Implementing a React-based frontend
- Supporting itinerary editing 