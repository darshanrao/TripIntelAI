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

// Search flights endpoint
app.post('/search-flights', async (req, res) => {
  // Simulate processing delay
  await delay(1500);
  
  const { message, conversation_id } = req.body;
  
  if (!message || message.trim() === '') {
    return res.status(400).json({
      success: false,
      error: 'Message is required for flight search'
    });
  }
  
  console.log(`Searching flights based on message: "${message}"`);
  
  // Create a search ID for tracking this search
  const searchId = uuidv4();
  
  // Get conversation or create a new one if not provided
  const conversationId = conversation_id || uuidv4();
  if (!conversations[conversationId]) {
    conversations[conversationId] = [];
  }
  
  // Add search confirmation to conversation
  conversations[conversationId].push({
    id: Date.now(),
    text: JSON.stringify({ message: `Searching for flights based on your request: "${message}"` }),
    sender: 'ai',
    timestamp: new Date()
  });
  
  // Return search ID and confirmation
  res.status(200).json({
    success: true,
    message: "Flight search initiated successfully",
    search_id: searchId,
    conversation_id: conversationId
  });
});

// Flight options endpoint (called after search)
app.post('/chat', async (req, res) => {
  // Simulate processing delay
  await delay(1000);
  
  const { message, conversation_id, request_flight_options, search_results_id } = req.body;
  
  if (!message || message.trim() === '') {
    return res.status(400).json({
      success: false,
      error: 'No message provided',
      response: JSON.stringify({ message: 'Error: No message provided' })
    });
  }
  
  // Get conversation or create a new one if not provided
  const conversationId = conversation_id || uuidv4();
  if (!conversations[conversationId]) {
    conversations[conversationId] = [];
  }
  
  // Add user message to conversation
  conversations[conversationId].push({
    id: Date.now(),
    text: message,
    sender: 'user',
    timestamp: new Date()
  });
  
  // Check if this is a request for flight options
  if (request_flight_options) {
    console.log(`Flight options requested with search ID: ${search_results_id || 'none'}`);
    
    // Return flight options
    return res.status(200).json({
      success: true,
      conversation_id: conversationId,
      interaction_type: 'flight_selection',
      message: "Here are some flight options for your trip. Please select one that best suits your needs:",
      data: {
        flights: mockFlights
      }
    });
  }
  
  // If not a flight options request, continue with normal chat processing
  
  // Generate a response based on message content
  const aiResponse = findResponseByKeywords(message);
  
  // Add AI response to conversation
  conversations[conversationId].push({
    id: Date.now() + 1,
    text: aiResponse,
    sender: 'ai',
    timestamp: new Date()
  });
  
  // Determine if we should include itinerary data
  const shouldIncludeItinerary = message.toLowerCase().includes('itinerary') || 
                               message.toLowerCase().includes('plan') || 
                               Math.random() < 0.2; // Occasionally include itinerary randomly
  
  const responseData = {
    success: true,
    conversation_id: conversationId,
    response: aiResponse,
    data: shouldIncludeItinerary ? mockItineraryData : null
  };
  
  res.status(200).json(responseData);
});

// Generate itinerary endpoint
app.post('/generate-itinerary', async (req, res) => {
  // Simulate processing delay
  await delay(2000);
  
  const { destination, start_date, end_date, preferences } = req.body;
  
  if (!destination) {
    return res.status(400).json({
      success: false,
      error: 'Destination is required'
    });
  }
  
  // Return mock itinerary data
  res.status(200).json({
    success: true,
    itinerary: mockItineraryData
  });
});

// Select flight endpoint
app.post('/select-flight', async (req, res) => {
  // Simulate processing delay
  await delay(1000);
  
  const { flight_id, conversation_id } = req.body;
  
  if (!flight_id) {
    return res.status(400).json({
      success: false,
      error: 'Flight ID is required'
    });
  }
  
  // Find the selected flight
  const selectedFlight = mockFlights.find(flight => flight.id === flight_id) || mockFlights[0];
  
  // Add a confirmation message to the conversation if conversation_id is provided
  if (conversation_id && conversations[conversation_id]) {
    const confirmationMessage = `You selected a ${selectedFlight.airline} flight (${selectedFlight.flight_number}) from ${selectedFlight.departure_city} (${selectedFlight.departure_airport}) to ${selectedFlight.arrival_city} (${selectedFlight.arrival_airport}), departing at ${new Date(selectedFlight.departure_time).toLocaleTimeString()} and arriving at ${new Date(selectedFlight.arrival_time).toLocaleTimeString()}. The total price is $${selectedFlight.price}.`;
    
    conversations[conversation_id].push({
      id: Date.now(),
      text: JSON.stringify({ message: confirmationMessage }),
      sender: 'ai',
      timestamp: new Date()
    });
  }
  
  // Update the mockItineraryData with the selected flight details
  const updatedItinerary = { ...mockItineraryData };
  
  // Find a transportation activity in the itinerary and update it
  Object.values(updatedItinerary.daily_itinerary).forEach(day => {
    if (day.activities) {
      day.activities.forEach(activity => {
        if (activity.type === 'transportation' && activity.category === 'flight') {
          activity.title = `${selectedFlight.airline} Flight ${selectedFlight.flight_number}`;
          activity.details = {
            ...activity.details,
            airline: selectedFlight.airline,
            flight_number: selectedFlight.flight_number,
            departure_time: new Date(selectedFlight.departure_time).toLocaleTimeString(),
            arrival_time: new Date(selectedFlight.arrival_time).toLocaleTimeString(),
            departure_airport: selectedFlight.departure_airport,
            arrival_airport: selectedFlight.arrival_airport,
            price: selectedFlight.price
          };
        }
      });
    }
  });
  
  res.status(200).json({
    success: true,
    interaction_type: 'feedback',
    message: `Your flight has been selected. ${selectedFlight.airline} ${selectedFlight.flight_number} from ${selectedFlight.departure_city} to ${selectedFlight.arrival_city} for $${selectedFlight.price}.`,
    data: updatedItinerary
  });
});

// Continue processing endpoint
app.post('/continue-processing', async (req, res) => {
  // Simulate processing delay
  await delay(1500);
  
  const { conversation_id } = req.body;
  
  if (!conversation_id) {
    return res.status(400).json({
      success: false,
      error: 'Conversation ID is required',
      response: JSON.stringify({ message: 'Error: Conversation ID is required' })
    });
  }
  
  res.status(200).json({
    success: true,
    response: JSON.stringify({ message: "I've updated your itinerary with your flight selection." }),
    data: mockItineraryData
  });
});

// Voice input endpoint (mock)
app.post('/voice-input', async (req, res) => {
  // Simulate processing delay
  await delay(2000);
  
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

// WebSocket endpoint (mock - returns success message)
app.get('/ws/:id', (req, res) => {
  res.status(200).json({
    message: "WebSocket would be available here in a real implementation.",
    note: "This mock backend only provides REST API endpoints."
  });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Mock backend server running on port ${PORT}`);
  console.log(`Available endpoints:`);
  console.log(`- GET  /health - Health check`);
  console.log(`- POST /conversations - Create a new conversation`);
  console.log(`- GET  /conversations/:id - Get conversation history`);
  console.log(`- POST /chat - Send a chat message (handles normal chat & flight options)`);
  console.log(`- POST /search-flights - Initiate a flight search from user message`);
  console.log(`- POST /select-flight - Select a flight and update itinerary`);
  console.log(`- POST /continue-processing - Continue processing after flight selection`);
  console.log(`- POST /voice-input - Process voice input`);
  console.log(`- POST /save-audio - Save and process audio recording (same as voice-input)`);
  console.log(`\nTo use the flight search flow:`);
  console.log(`1. POST /search-flights - Send user message about flight search`);
  console.log(`2. POST /chat with request_flight_options=true - Get flight options`);
  console.log(`3. POST /select-flight - Select a flight and get updated itinerary`);
}); 