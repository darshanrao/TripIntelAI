const { API_URL, USE_MOCKS } = require('./config');

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
 * @param {Object} options - Additional options like requestFlightOptions
 * @returns {Promise} - Promise with the response
 */
export const sendChatMessage = async (message, conversationId = null, options = {}) => {
  if (!message || message.trim() === '') {
    console.error('Empty message detected in sendChatMessage');
    return { 
      success: false, 
      error: 'No message provided',
      response: 'Error: No message provided'
    };
  }
  
  try {
    console.log('Sending message to API:', message, options);
    
    // Use the /chat endpoint and add step_by_step flag
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        message: message, // API expects message parameter
        conversation_id: conversationId,
        step_by_step: true, // Ensure step-by-step is sent
        request_flight_options: options.requestFlightOptions || false, // Add flag for flight options
        search_results_id: options.searchResults || null // Add search results ID from previous call
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
 * @param {string|number} flightIdOrIndex - ID or index of the selected flight
 * @param {string} conversationId - Conversation ID
 * @returns {Promise} - Promise with the response containing the itinerary
 */
export const selectFlight = async (flightIdOrIndex, conversationId) => {
  try {
    console.log(`Selecting flight ${flightIdOrIndex} for conversation ${conversationId}`);
    
    const response = await fetch(`${API_URL}/select-flight`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        flight_id: flightIdOrIndex, // API expects flight_id parameter
        conversation_id: conversationId
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
 * Continue processing after flight selection
 * @param {string} conversationId - Conversation ID
 * @returns {Promise} - Promise with the response containing the itinerary
 */
export const continueProcessing = async (conversationId) => {
  try {
    console.log(`Continuing processing for conversation ${conversationId}`);
    
    return await executeRequest('/continue-processing', 'POST', { 
      conversation_id: conversationId
    });
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
    
    const response = await fetch(`${API_URL}/search-flights`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        message: message,
        conversation_id: conversationId,
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