const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const { v4: uuidv4 } = require('uuid');
const { mockItineraryData, mockFlights, chatResponses, conversations } = require('./mockData');

// Create Express server
const app = express();
const PORT = process.env.PORT || 8000;

// Middleware
app.use(cors()); // Enable CORS for all routes
app.use(bodyParser.json()); // Parse JSON request bodies

// Helper functions
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const findResponseByKeywords = (message) => {
  // Check for keywords in the message
  const lowercaseMessage = message.toLowerCase();
  
  if (lowercaseMessage.includes('hello') || lowercaseMessage.includes('hi')) {
    return JSON.stringify({ message: chatResponses.hello });
  }
  if (lowercaseMessage.includes('tokyo')) {
    return JSON.stringify({ message: chatResponses.tokyo });
  }
  if (lowercaseMessage.includes('budget')) {
    return JSON.stringify({ message: chatResponses.budget });
  }
  if (lowercaseMessage.includes('flight')) {
    return JSON.stringify({ message: chatResponses.flight });
  }
  if (lowercaseMessage.includes('itinerary')) {
    return JSON.stringify({ message: chatResponses.itinerary });
  }
  if (lowercaseMessage.includes('hotel')) {
    return JSON.stringify({ message: chatResponses.hotel });
  }
  if (lowercaseMessage.includes('food')) {
    return JSON.stringify({ message: chatResponses.food });
  }
  if (lowercaseMessage.includes('activity')) {
    return JSON.stringify({ message: chatResponses.activity });
  }
  
  return JSON.stringify({ message: chatResponses.default });
};

// Routes

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', message: 'Mock backend is running' });
});

// Create a new conversation
app.post('/conversations', async (req, res) => {
  // Simulate processing delay
  await delay(300);
  
  // Generate a new conversation ID
  const conversationId = uuidv4();
  
  // Initialize conversation with a welcome message
  conversations[conversationId] = [
    {
      id: Date.now(),
      text: JSON.stringify({ message: "Hi there! I'm your AI travel assistant. Where would you like to go?" }),
      sender: 'ai',
      timestamp: new Date()
    }
  ];
  
  res.status(200).json({
    success: true,
    conversation_id: conversationId
  });
});

// Get conversation history
app.get('/conversations/:id', async (req, res) => {
  // Simulate processing delay
  await delay(300);
  
  const { id } = req.params;
  
  if (!conversations[id]) {
    return res.status(404).json({
      success: false,
      error: 'Conversation not found'
    });
  }
  
  res.status(200).json({
    success: true,
    conversation_id: id,
    messages: conversations[id]
  });
});

// Chat endpoint
app.post('/chat', async (req, res) => {
  // Simulate processing delay
  await delay(1000);
  
  const { type, message, conversation_id, data } = req.body;
  
  // Get conversation or create a new one if not provided
  const conversationId = conversation_id || uuidv4();
  if (!conversations[conversationId]) {
    conversations[conversationId] = [];
  }
  
  // Add user message to conversation if present
  if (message) {
    conversations[conversationId].push({
      id: Date.now(),
      text: message,
      sender: 'user',
      timestamp: new Date()
    });
  }
  
  // Handle different message types
  switch (type) {
    case 'initialize':
      // Initialize conversation with welcome message
      res.status(200).json({
        success: true,
        conversation_id: conversationId,
        type: 'initialize',
        message: "Hi there! I'm your AI travel assistant. Where would you like to go?"
      });
      break;
      
    case 'info':
      // Process initial trip information and search for flights
      const aiResponse = findResponseByKeywords(message);
      
      // Add AI response to conversation
      conversations[conversationId].push({
        id: Date.now() + 1,
        text: aiResponse,
        sender: 'ai',
        timestamp: new Date()
      });
      
      // Return flight search results
      res.status(200).json({
        success: true,
        conversation_id: conversationId,
        type: 'flight_search_outbound',
        message: "Here are some flight options for your trip. Please select one that best suits your needs:",
        data: {
          flights: mockFlights.map((flight, index) => ({
            ...flight,
            id: `dep-${index}`,
            flight_type: 'departure'
          }))
        }
      });
      break;
      
    case 'flight_select_outbound':
      // Process outbound flight selection and search for return flights
      const outboundFlight = mockFlights.find(f => f.id === data.selected_flight_id) || mockFlights[0];
      
      // Store the selected outbound flight in the conversation data
      if (!conversations[conversationId].data) {
        conversations[conversationId].data = {};
      }
      conversations[conversationId].data.selectedOutboundFlight = outboundFlight;
      
      res.status(200).json({
        success: true,
        conversation_id: conversationId,
        type: 'flight_search_inbound',
        message: "Great! Now please select your return flight:",
        data: {
          flights: mockFlights.map((flight, index) => ({
            ...flight,
            id: `ret-${index}`,
            flight_type: 'return',
            departure_city: flight.arrival_city,
            arrival_city: flight.departure_city,
            departure_airport: flight.arrival_airport,
            arrival_airport: flight.departure_airport
          }))
        }
      });
      break;
      
    case 'flight_select_inbound':
      // Process inbound flight selection and generate itinerary
      const inboundFlight = mockFlights.find(f => f.id === data.selected_flight_id) || mockFlights[1];
      
      // Get the previously selected outbound flight from conversation data
      const storedOutboundFlight = conversations[conversationId].data?.selectedOutboundFlight || mockFlights[0];
      
      // Create itinerary with selected flights
      const itinerary = {
        ...mockItineraryData,
        flights: {
          outbound: storedOutboundFlight,
          inbound: inboundFlight
        }
      };
      
      // Add AI response to conversation
      conversations[conversationId].push({
        id: Date.now() + 1,
        text: JSON.stringify({ 
          message: "Your itinerary has been generated with your selected flights. Check the itinerary view for details.",
          type: 'generate_itinerary',
          data: { itinerary }
        }),
        sender: 'ai',
        timestamp: new Date()
      });
      
      res.status(200).json({
        success: true,
        conversation_id: conversationId,
        type: 'generate_itinerary',
        message: "Your itinerary has been generated with your selected flights. Check the itinerary view for details.",
        data: {
          itinerary
        }
      });
      break;
      
    case 'chat':
      // Handle regular chat messages
      const response = findResponseByKeywords(message);
      
      // Add AI response to conversation
      conversations[conversationId].push({
        id: Date.now() + 1,
        text: response,
        sender: 'ai',
        timestamp: new Date()
      });
      
      res.status(200).json({
        success: true,
        conversation_id: conversationId,
        type: 'chat',
        message: JSON.parse(response).message
      });
      break;
      
    default:
      res.status(400).json({
        success: false,
        error: 'Invalid message type',
        message: 'Please provide a valid message type'
      });
  }
});

// Save audio endpoint (mirrors voice-input functionality)
app.post('/save-audio', async (req, res) => {
  // Simulate processing delay
  await delay(2000);
  
  // Check if request includes request_flight_options flag
  const requestFlightOptions = req.body.request_flight_options === 'true';
  
  // Generate a random transcript
  const transcripts = [
    "I want to visit Tokyo for a week.",
    "What are the best things to do in Tokyo?",
    "Can you suggest an itinerary for Tokyo?",
    "What's the budget I need for Tokyo?",
    "Tell me about flights to Tokyo."
  ];
  
  const transcript = transcripts[Math.floor(Math.random() * transcripts.length)];
  
  // Generate a response based on the transcript
  const aiResponse = findResponseByKeywords(transcript);
  
  // Determine if we should include itinerary data
  const shouldIncludeItinerary = transcript.toLowerCase().includes('itinerary') || 
                               transcript.toLowerCase().includes('plan') || 
                               Math.random() < 0.2; // Occasionally include itinerary randomly
  
  res.status(200).json({
    success: true,
    transcript: transcript,
    response: aiResponse,
    data: shouldIncludeItinerary ? mockItineraryData : null
  });
});

// NEW TRAVEL PLANNING API ENDPOINTS

// 1. Initiate Travel Planning Endpoint
app.post('/initiate-travel-planning', async (req, res) => {
  // Simulate processing delay
  await delay(800);
  
  const { destination, departure_date, return_date, num_travelers } = req.body;
  
  // Validate required fields
  const missingFields = [];
  if (!destination) missingFields.push('destination');
  if (!departure_date) missingFields.push('departure_date');
  if (!return_date) missingFields.push('return_date');
  if (!num_travelers) missingFields.push('num_travelers');
  
  // If any fields are missing, return an error response
  if (missingFields.length > 0) {
    return res.status(400).json({
      success: false,
      error: 'Missing required information',
      missing_fields: missingFields,
      message: `Please provide the following information: ${missingFields.join(', ')}`
    });
  }
  
  // All required information is present, create a planning session
  const planningId = uuidv4();
  
  // Return success response
  res.status(200).json({
    success: true,
    planning_id: planningId,
    message: "Travel planning initiated successfully. Proceeding to flight search.",
    travel_details: {
      destination,
      departure_date,
      return_date,
      num_travelers: parseInt(num_travelers)
    },
    next_step: "flight-search"
  });
});

// 2. Flight Search Endpoint
app.post('/flight-search', async (req, res) => {
  // Simulate processing delay
  await delay(1500);
  
  const { planning_id, destination, departure_date, return_date, num_travelers } = req.body;
  
  // Validate required fields
  if (!planning_id) {
    return res.status(400).json({
      success: false,
      error: 'Planning ID is required'
    });
  }
  
  // Check for other required parameters
  const missingFields = [];
  if (!destination) missingFields.push('destination');
  if (!departure_date) missingFields.push('departure_date');
  if (!return_date) missingFields.push('return_date');
  if (!num_travelers) missingFields.push('num_travelers');
  
  if (missingFields.length > 0) {
    return res.status(400).json({
      success: false,
      error: 'Missing required information',
      missing_fields: missingFields
    });
  }
  
  // Generate departure flights (hardcoded for testing)
  const departureFlights = mockFlights.map((flight, index) => ({
    ...flight,
    id: `dep-${index}`,
    departure_date: departure_date,
    flight_type: 'departure'
  }));
  
  // Generate return flights (hardcoded for testing)
  const returnFlights = mockFlights.map((flight, index) => ({
    ...flight,
    id: `ret-${index}`,
    departure_date: return_date,
    flight_type: 'return',
    // Swap departure and arrival cities for return flights
    departure_city: flight.arrival_city,
    arrival_city: flight.departure_city,
    departure_airport: flight.arrival_airport,
    arrival_airport: flight.departure_airport
  }));
  
  // Return flight search results
  res.status(200).json({
    success: true,
    planning_id: planning_id,
    message: "Flight search completed successfully",
    data: {
      departure_flights: departureFlights,
      return_flights: returnFlights,
      search_parameters: {
        destination,
        departure_date,
        return_date,
        num_travelers: parseInt(num_travelers)
      }
    },
    next_step: "flight-select"
  });
});

// 3. Flight Selection Endpoint
app.post('/flight-select', async (req, res) => {
  // Simulate processing delay
  await delay(1000);
  
  const { planning_id, departure_flight_id, return_flight_id } = req.body;
  
  // Validate required fields
  if (!planning_id) {
    return res.status(400).json({
      success: false,
      error: 'Planning ID is required'
    });
  }
  
  if (!departure_flight_id || !return_flight_id) {
    return res.status(400).json({
      success: false,
      error: 'Both departure and return flight IDs are required',
      missing_fields: !departure_flight_id ? ['departure_flight_id'] : ['return_flight_id']
    });
  }
  
  // Find selected flights (for a real implementation you would look these up in a database)
  const departureFlight = mockFlights[0]; // Just use the first mock flight for testing
  const returnFlight = { 
    ...mockFlights[1],
    departure_city: mockFlights[1].arrival_city,
    arrival_city: mockFlights[1].departure_city,
    departure_airport: mockFlights[1].arrival_airport,
    arrival_airport: mockFlights[1].departure_airport
  };
  
  // Return flight selection results
  res.status(200).json({
    success: true,
    planning_id: planning_id,
    message: "Flight selection confirmed",
    data: {
      selected_flights: {
        departure: departureFlight,
        return: returnFlight
      },
      total_price: (departureFlight.price + returnFlight.price).toFixed(2)
    },
    next_step: "generate-itinerary"
  });
});

// 4. Generate Itinerary Endpoint
app.post('/generate-itinerary', async (req, res) => {
  // Simulate processing delay for itinerary generation
  await delay(2000);
  
  const { planning_id, departure_flight_id, return_flight_id } = req.body;
  
  // Validate required fields
  if (!planning_id) {
    return res.status(400).json({
      success: false,
      error: 'Planning ID is required'
    });
  }
  
  if (!departure_flight_id || !return_flight_id) {
    return res.status(400).json({
      success: false,
      error: 'Both departure and return flight IDs are required'
    });
  }
  
  // Find selected flights (for a real implementation you would look these up in a database)
  const departureFlight = mockFlights[0]; // Just use the first mock flight for testing
  const returnFlight = { ...mockFlights[1] };
  
  // Create a copy of the mock itinerary and update it with flight information
  const itinerary = JSON.parse(JSON.stringify(mockItineraryData));
  
  // Add departure flight to itinerary (first day)
  if (itinerary.daily_itinerary.day_1 && itinerary.daily_itinerary.day_1.activities) {
    // Add as the first activity
    itinerary.daily_itinerary.day_1.activities.unshift({
      type: "transportation",
      category: "flight",
      title: `${departureFlight.airline} Flight ${departureFlight.flight_number}`,
      time: new Date(departureFlight.departure_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      duration_minutes: 240, // Example duration
      details: {
        airline: departureFlight.airline,
        flight_number: departureFlight.flight_number,
        departure_time: new Date(departureFlight.departure_time).toLocaleTimeString(),
        arrival_time: new Date(departureFlight.arrival_time).toLocaleTimeString(),
        departure_airport: departureFlight.departure_airport,
        arrival_airport: departureFlight.arrival_airport,
        price: departureFlight.price
      }
    });
  }
  
  // Add return flight to itinerary (last day)
  const lastDay = Object.keys(itinerary.daily_itinerary).pop();
  if (itinerary.daily_itinerary[lastDay] && itinerary.daily_itinerary[lastDay].activities) {
    // Add as the last activity
    itinerary.daily_itinerary[lastDay].activities.push({
      type: "transportation",
      category: "flight",
      title: `${returnFlight.airline} Flight ${returnFlight.flight_number}`,
      time: new Date(returnFlight.departure_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      duration_minutes: 240, // Example duration
      details: {
        airline: returnFlight.airline,
        flight_number: returnFlight.flight_number,
        departure_time: new Date(returnFlight.departure_time).toLocaleTimeString(),
        arrival_time: new Date(returnFlight.arrival_time).toLocaleTimeString(),
        departure_airport: returnFlight.arrival_airport, // Swap for return flight
        arrival_airport: returnFlight.departure_airport, // Swap for return flight
        price: returnFlight.price
      }
    });
  }
  
  // Return the complete itinerary
  res.status(200).json({
    success: true,
    planning_id: planning_id,
    message: "Itinerary generated successfully",
    data: {
      itinerary: itinerary,
      selected_flights: {
        departure: departureFlight,
        return: returnFlight
      },
      total_price: (departureFlight.price + returnFlight.price).toFixed(2)
    }
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Mock backend server running on port ${PORT}`);
  console.log(`Available endpoints:`);
  console.log(`- GET  /health - Health check`);
  console.log(`- POST /conversations - Create a new conversation`);
  console.log(`- GET  /conversations/:id - Get conversation history`);
  console.log(`- POST /chat - Send a chat message (general purpose)`);
  console.log(`- POST /save-audio - Process audio input`);
  
  // New structured travel planning API
  console.log(`\nTravel planning API endpoints:`);
  console.log(`- POST /initiate-travel-planning - Start travel planning session`);
  console.log(`- POST /flight-search - Search for flights`);
  console.log(`- POST /flight-select - Select departure and return flights`);
  console.log(`- POST /generate-itinerary - Generate complete itinerary`);
}); 