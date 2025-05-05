const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Send a chat message to the backend
 * @param {string} message - User's chat message
 * @param {string} conversationId - Optional conversation ID
 * @returns {Promise} - Promise with the response
 */
export const sendChatMessage = async (message, conversationId = null) => {
  try {
    // Use the /chat endpoint and add step_by_step flag
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        message: message,
        conversation_id: conversationId,
        interaction_type: 'chat',
        metadata: {
          step_by_step: true
        }
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
        conversation_id: conversationId,
        interaction_type: 'flight_selection',
        selection_data: {
          flight_index: flightIndex
        },
        metadata: {
          step_by_step: true
        }
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
        metadata: {
          step_by_step: true
        }
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