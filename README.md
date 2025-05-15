# TripIntel AI - Intelligent Travel Planning Assistant


[![TripIntel AI Demo](https://img.youtube.com/vi/rXdrZjP-H3U/0.jpg)](https://www.youtube.com/watch?v=rXdrZjP-H3U)

## Problem Statement

Planning a trip can be overwhelming and time-consuming, requiring users to:
- Research destinations and attractions
- Compare flight options and prices
- Find suitable accommodations
- Discover local restaurants and activities
- Calculate budgets and travel times
- Coordinate multiple aspects of the trip

Traditional travel planning often involves:
- Visiting multiple websites
- Manually comparing options
- Dealing with information overload
- Making decisions without comprehensive context
- Spending hours on research and coordination

## Solution: TripIntel AI

TripIntel AI is an intelligent travel planning assistant that uses advanced AI and natural language processing to create personalized travel itineraries. It leverages LangGraph for orchestration and Claude for natural language understanding to provide a seamless, conversational travel planning experience.

## Key Features

1. **Natural Language Interface**
   - Conversational interaction with the AI assistant
   - Understands complex travel queries and preferences
   - Handles follow-up questions and modifications

2. **Intelligent Itinerary Planning**
   - Multi-day trip planning with daily schedules
   - Smart activity sequencing and time management
   - Balance between popular attractions and local experiences

3. **Comprehensive Travel Components**
   - Flight search and booking recommendations
   - Hotel and accommodation options
   - Local attractions and activities
   - Restaurant recommendations
   - Route planning and transportation options

4. **Interactive Planning Process**
   - Real-time feedback and modifications
   - Budget considerations and adjustments
   - Preference-based customization
   - Validation of travel parameters

## Technical Architecture

The system is built using a LangGraph pipeline with the following components:

1. **Core Nodes**
   - `ChatInputNode`: Processes natural language input from users
   - `IntentParserNode`: Extracts structured travel intent from user queries
   - `TripValidatorNode`: Validates trip parameters and handles missing information
   - `AgentSelectorNode`: Determines which specialized nodes to call based on user needs

2. **Specialized Agent Nodes**
   - `FlightsNode`: Searches and recommends flight options
   - `HotelNode`: Finds suitable accommodation options
   - `AttractionsNode`: Discovers local attractions and activities
   - `RestaurantsNode`: Finds dining options
   - `ItineraryPlannerNode`: Creates daily schedules and manages the overall itinerary

3. **Support Nodes**
   - `ProcessResponseNode`: Handles user feedback and additional information
   - `EndNode`: Finalizes the planning process and returns the complete itinerary

The graph follows a sequential flow:
1. User input is processed through core nodes
2. Validation ensures all necessary information is available
3. Specialized agents gather travel components in sequence:
   - Flights → Hotels → Attractions → Restaurants
4. The itinerary planner creates a cohesive schedule
5. User feedback is handled through the process response node
6. The process continues until all days are planned

## Technology Stack

- **Backend Framework**: FastAPI
- **AI/ML**: 
  - LangGraph for workflow orchestration
  - Claude for natural language processing
  - Gemini for additional AI capabilities
- **APIs**:
  - Google Places API for location data
  - Flight booking APIs
  - Maps and routing services
- **Frontend**: Modern web interface with real-time updates

## Getting Started

1. **Prerequisites**
   - Python 3.8+
   - API keys for required services
   - Virtual environment

2. **Installation**
   ```bash
   git clone https://github.com/yourusername/tripintel-ai.git
   cd tripintel-ai
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configuration**
   Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   GOOGLE_PLACES_API_KEY=your_google_places_api_key
   PERPLEXITY_API_KEY=your_perplexity_api_key
   ```

4. **Running the Application**
   ```bash
   # Development mode
   DEV_MODE=true python run.py
   
   # Production mode
   python run.py
   ```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- LangGraph team for the workflow orchestration framework
- Anthropic for Claude AI capabilities
- Google for Places API and mapping services

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
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_PLACES_API_KEY=your_google_places_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
```

### API Keys
- **Gemini API Key**: Get one from the [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Google Places API Key**: Get one from the [Google Cloud Console](https://console.cloud.google.com/) with the Places API enabled
- **Perplexity API Key**: Get one from the [Perplexity AI Platform](https://www.perplexity.ai/api)

## Running the Application

### Development Mode

Run the application in development mode with hot reload:
```bash
DEV_MODE=true python run.py
```

### Production Mode

Run the application in production mode:
```bash
python run.py
```

For production deployments with multiple workers, use Gunicorn:
```bash
gunicorn -c gunicorn_conf.py app.main:app
```

### Preventing Duplicate Processing

If you experience duplicate request processing or database connections, try the following:

1. **Set DEV_MODE correctly**:
   - Use `DEV_MODE=true` only during development
   - In production, make sure `DEV_MODE` is not set or explicitly set to `false`

2. **Use Gunicorn with proper worker configuration**:
   - The included `gunicorn_conf.py` has optimal settings
   - Adjust worker count based on your server's CPU cores

3. **Monitor request processing**:
   - Check logs for duplicate processing patterns
   - Use tools like New Relic or Prometheus to monitor request processing times

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
