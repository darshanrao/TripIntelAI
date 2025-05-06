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
  
  const { message, conversation_id } = req.body;
  
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

// Search flights endpoint
app.post('/search-flights', async (req, res) => {
  // Simulate processing delay
  await delay(1500);
  
  const { origin, destination, departure_date } = req.body;
  
  if (!origin || !destination) {
    return res.status(400).json({
      success: false,
      error: 'Origin and destination are required'
    });
  }
  
  // Return mock flights
  res.status(200).json({
    success: true,
    flights: mockFlights
  });
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
    const confirmationMessage = `You selected a flight with ${selectedFlight.airline}, departing at ${new Date(selectedFlight.departure_time).toLocaleTimeString()} and arriving at ${new Date(selectedFlight.arrival_time).toLocaleTimeString()}.`;
    conversations[conversation_id].push({
      id: Date.now(),
      text: JSON.stringify({ message: confirmationMessage }),
      sender: 'ai',
      timestamp: new Date()
    });
  }
  
  res.status(200).json({
    success: true,
    response: JSON.stringify({ message: `Flight booked with ${selectedFlight.airline}` }),
    data: {
      flight: selectedFlight,
      itinerary: mockItineraryData
    }
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
  console.log(`- POST /chat - Send a chat message`);
  console.log(`- POST /search-flights - Search for flights`);
  console.log(`- POST /generate-itinerary - Generate an itinerary`);
  console.log(`- POST /select-flight - Select a flight`);
  console.log(`- POST /continue-processing - Continue processing`);
  console.log(`- POST /voice-input - Process voice input`);
}); 