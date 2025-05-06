// Mock API service that replaces the real API service for frontend testing
import { mockItineraryData, mockChatHistory, getMockResponse, delay } from './mockData';

// Keep track of the mock conversation
let currentConversationId = 'mock-conv-' + Date.now();
let conversationHistory = [...mockChatHistory];

/**
 * Send a chat message to the mock backend
 * @param {string} message - User's chat message
 * @param {string} conversationId - Optional conversation ID
 * @returns {Promise} - Promise with the response
 */
export const sendChatMessage = async (message) => {
  if (!message || message.trim() === '') {
    console.error('Empty message detected in sendChatMessage');
    return { 
      success: false, 
      error: 'No message provided',
      response: 'Error: No message provided'
    };
  }
  
  try {
    console.log('Sending mock message:', message);
    
    // Add user message to history
    const userMessage = {
      id: Date.now(),
      text: message,
      sender: 'user',
      timestamp: new Date()
    };
    conversationHistory.push(userMessage);
    
    // Get mock response
    const response = await getMockResponse(message);
    
    // Add AI response to history
    if (response.success) {
      const aiMessage = {
        id: Date.now() + 1,
        text: response.response,
        sender: 'ai',
        timestamp: new Date()
      };
      conversationHistory.push(aiMessage);
    }
    
    return response;
  } catch (error) {
    console.error('Mock API error:', error);
    return {
      success: false,
      error: error.message,
      response: 'Sorry, there was an error processing your request.'
    };
  }
};

/**
 * Create a new conversation
 * @returns {Promise} - Promise with the conversation ID
 */
export const createConversation = async () => {
  await delay(300); // Simulate network delay
  
  // Reset conversation history to initial state
  conversationHistory = [...mockChatHistory];
  
  // Generate new conversation ID
  currentConversationId = 'mock-conv-' + Date.now();
  
  return {
    success: true,
    conversation_id: currentConversationId
  };
};

/**
 * Get conversation history
 * @returns {Promise} - Promise with the conversation history
 */
export const getConversationHistory = async () => {
  await delay(500); // Simulate network delay
  
  return {
    success: true,
    conversation_id: currentConversationId,
    messages: conversationHistory
  };
};

/**
 * Save audio recording (mock)
 * @param {Blob} audioBlob - Recorded audio file as Blob
 * @returns {Promise} - Promise with the response
 */
export const saveAndProcessAudio = async (audioBlob) => {
  // Simulate processing delay
  await delay(2000);
  
  // Generate random transcript based on audio size
  const transcripts = [
    "I want to visit Tokyo for a week.",
    "What are the best things to do in Tokyo?",
    "Can you suggest an itinerary for Tokyo?",
    "What's the budget I need for Tokyo?",
    "Tell me about flights to Tokyo."
  ];
  
  // Pick a random transcript
  const transcript = transcripts[Math.floor(Math.random() * transcripts.length)];
  
  // Process the transcript to get a response
  const response = await getMockResponse(transcript);
  
  // Add messages to conversation history
  conversationHistory.push({
    id: Date.now(),
    text: transcript,
    sender: 'user',
    timestamp: new Date(),
    isTranscript: true
  });
  
  if (response.success) {
    conversationHistory.push({
      id: Date.now() + 1,
      text: response.response,
      sender: 'ai',
      timestamp: new Date()
    });
  }
  
  return {
    success: true,
    transcript: transcript,
    response: response.response,
    data: response.data
  };
};

/**
 * Select a flight (mock)
 * @param {number} flightIndex - Index of the selected flight
 * @returns {Promise} - Promise with the response
 */
export const selectFlight = async (flightIndex) => {
  await delay(1000); // Simulate network delay
  
  const selectedFlight = mockItineraryData.flights[flightIndex] || mockItineraryData.flights[0];
  
  // Add a confirmation message to the conversation
  conversationHistory.push({
    id: Date.now(),
    text: `You selected a flight with ${selectedFlight.airline}, departing at ${new Date(selectedFlight.departure_time).toLocaleTimeString()} and arriving at ${new Date(selectedFlight.arrival_time).toLocaleTimeString()}.`,
    sender: 'ai',
    timestamp: new Date()
  });
  
  return {
    success: true,
    response: `Flight booked with ${selectedFlight.airline}`,
    data: {
      flight: selectedFlight,
      itinerary: mockItineraryData
    }
  };
};

/**
 * Continue processing (mock)
 * @returns {Promise} - Promise with the response
 */
export const continueProcessing = async () => {
  await delay(1500); // Simulate network delay
  
  return {
    success: true,
    response: "I've updated your itinerary with your flight selection.",
    data: mockItineraryData
  };
}; 