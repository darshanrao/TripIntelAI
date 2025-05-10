const { API_URL, USE_MOCKS } = require('./config');
import { v4 as uuidv4 } from 'uuid';

// Keep track of in-flight requests to prevent duplicates
const pendingRequests = new Map();
// Map to track recently made requests by their parameters hash
const recentRequests = new Map();
// Default cache expiration time (ms)
const CACHE_EXPIRATION = 1000;

/**
 * Generate a unique hash for request parameters to detect duplicates
 * @param {string} endpoint - API endpoint
 * @param {object} params - Request parameters
 * @returns {string} - Hash string 
 */
const generateRequestHash = (endpoint, params) => {
  return `${endpoint}:${JSON.stringify(params)}`;
};

/**
 * Execute a request with deduplication
 * @param {string} endpoint - API endpoint
 * @param {string} method - HTTP method
 * @param {object} data - Request body
 * @param {FormData|null} formData - Form data for file uploads
 * @returns {Promise} - Promise with response
 */
const executeRequest = async (endpoint, method, data = null, formData = null) => {
  const fullUrl = `${API_URL}${endpoint}`;
  const requestKey = generateRequestHash(fullUrl, data || formData);
  
  // Check if an identical request was recently made
  if (recentRequests.has(requestKey)) {
    console.log(`Returning cached response for ${endpoint}`);
    return recentRequests.get(requestKey);
  }
  
  // Check if same request is in flight - return the existing promise
  if (pendingRequests.has(requestKey)) {
    console.log(`Request to ${endpoint} already in progress, reusing promise`);
    return pendingRequests.get(requestKey);
  }
  
  // Prepare request options
  const options = {
    method,
    headers: formData ? {} : { 'Content-Type': 'application/json' },
    body: formData || (data ? JSON.stringify(data) : undefined),
  };
  
  // Add X-Request-ID header for idempotency
  options.headers = {
    ...options.headers, 
    'X-Request-ID': `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  };

  // Create the request promise
  const requestPromise = (async () => {
    try {
      console.log(`Executing request to ${endpoint}`);
      const response = await fetch(fullUrl, options);
      
      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      // Cache the result briefly to prevent duplicates
      recentRequests.set(requestKey, result);
      setTimeout(() => recentRequests.delete(requestKey), CACHE_EXPIRATION);
      
      return result;
    } finally {
      // Remove from pending requests when done
      pendingRequests.delete(requestKey);
    }
  })();
  
  // Store the promise
  pendingRequests.set(requestKey, requestPromise);
  return requestPromise;
};

/**
 * Send a chat message to the backend
 * @param {string} message - User's chat message
 * @param {string} conversationId - Optional conversation ID
 * @param {string} type - Message type
 * @param {Object} data - Additional data for the message
 * @returns {Promise} - Promise with the response
 */
export const sendChatMessage = async (message, conversationId = null, type = 'info', data = {}) => {
  return executeRequest('/chat', 'POST', {
    type,
    message,
    conversation_id: conversationId,
    data
  });
};

/**
 * Create a new conversation
 * @returns {Promise} - Promise with the conversation ID
 */
export const createConversation = async () => {
  try {
    const response = await fetch(`${API_URL}/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error:', error);
    throw error;
  }
};

/**
 * Get conversation history
 * @param {string} conversationId - Conversation ID
 * @returns {Promise} - Promise with the conversation history
 */
export const getConversationHistory = async (conversationId) => {
  try {
    const response = await fetch(`${API_URL}/conversations/${conversationId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error:', error);
    throw error;
  }
};

/**
 * Send audio recording to the backend
 * @param {Blob} audioBlob - Recorded audio file as Blob
 * @returns {Promise} - Promise with the response
 */
export const sendAudioMessage = async (audioBlob) => {
  try {
    // Create form data to send the file
    const formData = new FormData();
    
    // Always use .mp3 extension and explicitly set the content type
    const file = new File([audioBlob], 'recording.mp3', { 
      type: 'audio/mpeg' 
    });
    
    formData.append('file', file);
    
    console.log(`Sending audio file: ${file.name}, size: ${file.size} bytes, type: ${file.type}`);

    const response = await fetch(`${API_URL}/voice-input`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error:', error);
    throw error;
  }
};

/**
 * Save a trip
 * @param {Object} tripData - Trip data object
 * @param {string} name - Optional trip name
 * @returns {Promise} - Promise with the saved trip
 */
export const saveTrip = async (tripData, name = null) => {
  try {
    const response = await fetch(`${API_URL}/trips`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        trip_data: tripData,
        name,
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error:', error);
    throw error;
  }
};

/**
 * Send audio recording to the new save-audio endpoint
 * @param {Blob} audioBlob - Recorded audio file as Blob
 * @param {Object} options - Additional options like requestFlightOptions
 * @returns {Promise} - Promise with the response
 */
export const saveAndProcessAudio = async (audioBlob, options = {}) => {
  try {
    // Create form data to send the file
    const formData = new FormData();
    
    // Add audio file
    // Always use .mp3 extension and explicitly set the content type
    const file = new File([audioBlob], 'recording.mp3', { 
      type: 'audio/mpeg' 
    });
    formData.append('file', file);
    
    // Add flag for flight options if needed
    if (options.requestFlightOptions) {
      formData.append('request_flight_options', 'true');
    }
    
    console.log(`Sending audio file: ${file.name}, size: ${file.size} bytes, type: ${file.type}`, options);

    const response = await fetch(`${API_URL}/save-audio`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error:', error);
    throw error;
  }
};

/**
 * Select a flight option from the presented choices
 * @param {string|number} returnFlightIdOrIndex - ID or index of the selected return flight
 * @param {string} conversationId - Conversation ID used as the planning ID
 * @param {string|number} departureFlightId - Optional ID of the previously selected departure flight
 * @returns {Promise} - Promise with the response containing the itinerary
 */
export const selectFlight = async (returnFlightIdOrIndex, conversationId, departureFlightId = 'dep-0') => {
  try {
    console.log(`Selecting flights - return: ${returnFlightIdOrIndex}, departure: ${departureFlightId}, conversation ID: ${conversationId}`);
    
    // When using the old API, we're selecting a single flight
    // In the new API, we need both departure and return flights
    
    const response = await fetch(`${API_URL}/flight-select`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        planning_id: conversationId,
        departure_flight_id: departureFlightId,
        return_flight_id: returnFlightIdOrIndex
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    const flightSelectionResponse = await response.json();
    
    // After selecting flights, immediately generate the itinerary
    const itineraryResponse = await fetch(`${API_URL}/generate-itinerary`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        planning_id: conversationId,
        departure_flight_id: departureFlightId,
        return_flight_id: returnFlightIdOrIndex
      }),
    });
    
    if (!itineraryResponse.ok) {
      throw new Error(`Error generating itinerary: ${itineraryResponse.statusText}`);
    }
    
    const finalResponse = await itineraryResponse.json();
    
    // Format the response to match the original API
    return {
      success: true,
      interaction_type: 'feedback',
      message: `Your flights have been selected. Outbound: ${flightSelectionResponse.data?.selected_flights?.departure?.airline || 'Airline'} flight to ${flightSelectionResponse.data?.selected_flights?.departure?.arrival_city || 'destination'}. Return: ${flightSelectionResponse.data?.selected_flights?.return?.airline || 'Airline'} flight to ${flightSelectionResponse.data?.selected_flights?.return?.arrival_city || 'origin'}.`,
      data: finalResponse.data.itinerary
    };
  } catch (error) {
    console.error('API error:', error);
    throw error;
  }
};

/**
 * Continue processing after flight selection
 * @param {string} conversationId - Conversation ID
 * @returns {Promise} - Promise with the response containing the itinerary
 */
export const continueProcessing = async (conversationId) => {
  try {
    console.log(`Continuing processing for conversation ${conversationId}`);
    
    // In the new API, we should already have the itinerary from the flight selection
    // But for backward compatibility, we'll regenerate it
    
    const response = await fetch(`${API_URL}/generate-itinerary`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        planning_id: conversationId,
        departure_flight_id: 'dep-0', // Default IDs since we don't know the actual IDs here
        return_flight_id: 'ret-0'
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }
    
    const finalResponse = await response.json();
    
    // Format the response to match the original API
    return {
      success: true,
      message: "Itinerary generated successfully",
      data: finalResponse.data.itinerary
    };
  } catch (error) {
    console.error('API error continuing processing:', error);
    throw error;
  }
};

/**
 * Search for flights based on user criteria
 * @param {string} message - User's search criteria message
 * @param {string} conversationId - Optional conversation ID
 * @returns {Promise} - Promise with flight search results
 */
export const searchFlights = async (message, conversationId = null) => {
  try {
    console.log('Searching flights with criteria:', message);
    
    // First, create a planning session
    const planningId = conversationId || uuidv4();
    
    // Extract basic information from message (simplified for mock)
    // In a real implementation, this would use NLP to extract destination, dates, etc.
    const today = new Date();
    const departureDate = new Date(today);
    departureDate.setDate(today.getDate() + 7); // Default: 1 week from now
    
    const returnDate = new Date(today);
    returnDate.setDate(today.getDate() + 14); // Default: 2 weeks from now
    
    // Format dates as YYYY-MM-DD
    const formatDate = (date) => {
      return date.toISOString().split('T')[0];
    };
    
    // First create a planning session
    const planningResponse = await fetch(`${API_URL}/initiate-travel-planning`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        destination: "Los Angeles", // Default destination (extracted from message in real implementation)
        departure_date: formatDate(departureDate),
        return_date: formatDate(returnDate),
        num_travelers: 1
      }),
    });
    
    if (!planningResponse.ok) {
      throw new Error(`Error: ${planningResponse.statusText}`);
    }
    
    const initResponse = await planningResponse.json();
    
    // Now search for flights
    const response = await fetch(`${API_URL}/flight-search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        planning_id: initResponse.planning_id,
        destination: "Los Angeles", 
        departure_date: formatDate(departureDate), 
        return_date: formatDate(returnDate), 
        num_travelers: 1
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    const flightSearchResponse = await response.json();
    
    // Format the response to match the original API
    return {
      success: true,
      message: "Flight search initiated successfully",
      search_id: flightSearchResponse.planning_id,
      conversation_id: conversationId || flightSearchResponse.planning_id
    };
  } catch (error) {
    console.error('Flight search API error:', error);
    throw error;
  }
};

/**
 * Initiate travel planning with basic trip parameters
 * @param {string} destination - Destination city or country
 * @param {string} departureDate - Departure date (YYYY-MM-DD)
 * @param {string} returnDate - Return date (YYYY-MM-DD)
 * @param {number} numTravelers - Number of travelers
 * @returns {Promise} - Promise with the response
 */
export const initiateTravelPlanning = async (destination, departureDate, returnDate, numTravelers) => {
  try {
    console.log('Initiating travel planning with:', { destination, departureDate, returnDate, numTravelers });
    
    const response = await fetch(`${API_URL}/initiate-travel-planning`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        destination, 
        departure_date: departureDate, 
        return_date: returnDate, 
        num_travelers: numTravelers 
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error initiating travel planning:', error);
    throw error;
  }
};

/**
 * Search for flights with the provided planning parameters
 * @param {string} planningId - Planning session ID 
 * @param {string} destination - Destination city
 * @param {string} departureDate - Departure date
 * @param {string} returnDate - Return date
 * @param {number} numTravelers - Number of travelers
 * @returns {Promise} - Promise with flight search results
 */
export const searchFlightsV2 = async (planningId, destination, departureDate, returnDate, numTravelers) => {
  try {
    console.log('Searching flights with params:', { planningId, destination, departureDate, returnDate, numTravelers });
    
    const response = await fetch(`${API_URL}/flight-search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        planning_id: planningId,
        destination, 
        departure_date: departureDate, 
        return_date: returnDate, 
        num_travelers: numTravelers 
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Flight search API error:', error);
    throw error;
  }
};

/**
 * Select departure and return flights
 * @param {string} planningId - Planning session ID
 * @param {string} departureFlightId - Selected departure flight ID
 * @param {string} returnFlightId - Selected return flight ID
 * @returns {Promise} - Promise with flight selection confirmation
 */
export const selectFlightsV2 = async (planningId, departureFlightId, returnFlightId) => {
  try {
    console.log('Selecting flights:', { planningId, departureFlightId, returnFlightId });
    
    const response = await fetch(`${API_URL}/flight-select`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        planning_id: planningId,
        departure_flight_id: departureFlightId,
        return_flight_id: returnFlightId
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error selecting flights:', error);
    throw error;
  }
};

/**
 * Generate complete travel itinerary
 * @param {string} planningId - Planning session ID
 * @param {string} departureFlightId - Selected departure flight ID
 * @param {string} returnFlightId - Selected return flight ID
 * @returns {Promise} - Promise with the generated itinerary
 */
export const generateItinerary = async (planningId, departureFlightId, returnFlightId) => {
  try {
    console.log('Generating itinerary:', { planningId, departureFlightId, returnFlightId });
    
    const response = await fetch(`${API_URL}/generate-itinerary`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        planning_id: planningId,
        departure_flight_id: departureFlightId,
        return_flight_id: returnFlightId
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error generating itinerary:', error);
    throw error;
  }
}; 