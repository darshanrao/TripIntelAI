const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Send a chat message to the backend
 * @param {string} message - User's chat message
 * @param {string} conversationId - Optional conversation ID
 * @returns {Promise} - Promise with the response
 */
export const sendChatMessage = async (message, conversationId = null) => {
  if (!message || message.trim() === '') {
    console.error('Empty message detected in sendChatMessage');
    return { 
      success: false, 
      error: 'No message provided',
      response: 'Error: No message provided'
    };
  }
  
  try {
    console.log('Sending message to API:', message);
    
    // Use the /chat endpoint and add step_by_step flag
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        message: message, // API expects message parameter
        conversation_id: conversationId,
        step_by_step: true // Ensure step-by-step is sent
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
    console.error('API error sending audio:', error);
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
 * @returns {Promise} - Promise with the response
 */
export const saveAndProcessAudio = async (audioBlob) => {
  try {
    // Create form data to send the file
    const formData = new FormData();
    
    // Always use .mp3 extension and explicitly set content type
    const file = new File([audioBlob], 'recording.mp3', { 
      type: 'audio/mpeg' 
    });
    
    formData.append('file', file);
    
    console.log(`Saving and processing audio file: ${file.name}, size: ${file.size} bytes, type: ${file.type}`);

    const response = await fetch(`${API_URL}/save-audio`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error processing audio:', error);
    throw error;
  }
};

/**
 * Select a flight option from the presented choices
 * @param {number} flightIndex - Index of the selected flight
 * @param {string} conversationId - Conversation ID
 * @returns {Promise} - Promise with the response containing the itinerary
 */
export const selectFlight = async (flightIndex, conversationId) => {
  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        selection_type: 'flight',
        selection_index: flightIndex,
        conversation_id: conversationId,
        step_by_step: true // Add this flag to indicate step-by-step mode
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
    const response = await fetch(`${API_URL}/continue-processing`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        conversation_id: conversationId,
        step_by_step: true
      }),
    });

    if (!response.ok) {
      throw new Error(`Error: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API error continuing processing:', error);
    throw error;
  }
}; 