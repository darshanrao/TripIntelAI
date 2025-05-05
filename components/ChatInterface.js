import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaMicrophone, FaPaperPlane, FaStop } from 'react-icons/fa';
import { sendChatMessage, createConversation, saveAndProcessAudio, selectFlight, continueProcessing } from '../services/api';
import tripPlannerWebSocket from '../services/websocket';
import FlightSelection from './FlightSelection';

const TypingIndicator = () => (
  <div className="flex items-center space-x-1 py-1">
    <div className="typing-dot"></div>
    <div className="typing-dot"></div>
    <div className="typing-dot"></div>
  </div>
);

const ChatInterface = ({ onSendMessage, apiResponse }) => {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hi there! I'm your AI travel assistant. Where would you like to go?", sender: 'ai', timestamp: new Date() }
  ]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [flightOptions, setFlightOptions] = useState(null);
  const messageEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  
  // Audio recording refs
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);

  // Initialize conversation when component mounts
  useEffect(() => {
    const initConversation = async () => {
      try {
        const response = await createConversation();
        if (response && response.conversation_id) {
          console.log('Conversation created with ID:', response.conversation_id);
          setConversationId(response.conversation_id);
        } else {
          console.error('Failed to create conversation: Invalid response', response);
        }
      } catch (error) {
        console.error('Failed to create conversation:', error);
      }
    };
    
    initConversation();
  }, []);

  // Function to check supported MIME types, prioritizing MP3
  const getSupportedMimeType = () => {
    // Test and log all supported formats
    const allTypes = [
      'audio/mpeg',
      'audio/mp3',
      'audio/webm',
      'audio/webm;codecs=opus',
      'audio/webm;codecs=mp3',
      'audio/ogg;codecs=opus',
      'audio/wav',
      'audio/mp4'
    ];
    
    console.log('Checking supported audio formats...');
    allTypes.forEach(type => {
      console.log(`${type}: ${MediaRecorder.isTypeSupported(type) ? 'Supported' : 'Not supported'}`);
    });
    
    // Prefer MP3 format if supported
    if (MediaRecorder.isTypeSupported('audio/mp3')) {
      return 'audio/mp3';
    }
    if (MediaRecorder.isTypeSupported('audio/mpeg')) {
      return 'audio/mpeg';
    }
    
    // Fall back to these formats in order of preference
    for (const type of allTypes) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }
    
    // Final fallback
    return 'audio/webm';
  };

  // Audio recording implementation
  const startRecording = async () => {
    if (isRecording) return;
    
    try {
      // Request microphone permission with specific constraints
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 44100,
          echoCancellation: true,
          noiseSuppression: true,
        } 
      });
      streamRef.current = stream;
      
      // Get supported MIME type
      const mimeType = getSupportedMimeType();
      console.log(`Using MIME type: ${mimeType}`);
      
      // Initialize the media recorder with proper MIME type
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 128000 // 128 kbps for better quality
      });
      mediaRecorderRef.current = mediaRecorder;
      
      // Clear previous chunks
      audioChunksRef.current = [];
      
      // Handle data available event to collect audio chunks
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          console.log(`Received audio chunk: ${event.data.size} bytes`);
          audioChunksRef.current.push(event.data);
        } else {
          console.warn('Received empty audio chunk');
        }
      };
      
      // Handle recording stop event to process the recording
      mediaRecorder.onstop = async () => {
        if (audioChunksRef.current.length === 0) {
          console.error('No audio data collected');
          setIsRecording(false);
          return;
        }
        
        // Create audio blob from collected chunks with correct MIME type
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        console.log(`Recording complete, blob size: ${audioBlob.size} bytes, chunks: ${audioChunksRef.current.length}`);
        
        if (audioBlob.size < 100) {
          console.error('Audio recording too small, likely no data captured');
          setMessages(prev => [...prev, {
            id: Date.now() + 1,
            text: "The recording was too short or no audio was captured. Please try again.",
            sender: 'ai',
            timestamp: new Date()
          }]);
          return;
        }
        
        // Save the audio locally for debugging (optional)
        try {
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          
          // Log for debugging
          console.log(`Audio URL created: ${audioUrl}`);
          console.log(`You can listen to the recording in the console by running:
            const audio = new Audio('${audioUrl}');
            audio.play();
          `);
        } catch (error) {
          console.error('Error creating audio URL:', error);
        }
        
        // Show recording processing message
        const processingMessage = {
          id: Date.now(),
          text: "Processing your voice message...",
          sender: 'ai',
          timestamp: new Date(),
          isTemporary: true // Mark as temporary so we can remove it later
        };
        setMessages(prev => [...prev, processingMessage]);
        
        try {
          // Send the audio to the backend
          setIsTyping(true);
          const response = await saveAndProcessAudio(audioBlob);
          
          // Remove the processing message
          setMessages(prev => prev.filter(msg => !msg.isTemporary));
          
          // Handle the response from the new endpoint
          console.log('Audio processing response:', response);
          
          if (response.success) {
            // Add the transcription message
            if (response.transcript) {
              setMessages(prev => [...prev, {
                id: Date.now(),
                text: `I heard: "${response.transcript}"`,
                sender: 'ai',
                timestamp: new Date(),
                isTranscript: true
              }]);
            }
            
            // Add AI response to chat
            const aiResponse = {
              id: Date.now() + 1,
              text: response.response,
              sender: 'ai',
              timestamp: new Date()
            };
            
            setMessages(prev => [...prev, aiResponse]);
            
            // Notify parent component with the transcript or response
            onSendMessage(response.transcript || response.response);
          } else {
            // Error case
            setMessages(prev => [...prev, {
              id: Date.now() + 1,
              text: response.response || "Sorry, I couldn't process your audio. Please try again.",
              sender: 'ai',
              timestamp: new Date()
            }]);
          }
          
          setIsTyping(false);
        } catch (error) {
          console.error('Error processing voice message:', error);
          setIsTyping(false);
          
          // Add error message
          setMessages(prev => prev.filter(msg => !msg.isTemporary));
          setMessages(prev => [...prev, {
            id: Date.now() + 1,
            text: "Sorry, I had trouble understanding your voice message. Could you type it instead?",
            sender: 'ai',
            timestamp: new Date()
          }]);
        }
        
        // Stop all tracks on the stream
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
      };
      
      // Start recording and request data at regular intervals (1 second)
      mediaRecorder.start(1000);
      setIsRecording(true);
      
      // Add recording indicator message
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: "Recording audio...",
        sender: 'user',
        timestamp: new Date(),
        isRecording: true // Special flag for recording indicator
      }]);
      
    } catch (error) {
      console.error('Error starting audio recording:', error);
      alert('Could not access your microphone. Please check your browser permissions and try again.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      // Stop the media recorder
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Remove the recording indicator message
      setMessages(prev => prev.filter(msg => !msg.isRecording));
    }
  };

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle flight selection
  const handleFlightSelection = async (flightIndex) => {
    if (!conversationId) {
      console.error('No conversation ID available');
      return;
    }
    
    console.log(`Selected flight index: ${flightIndex}, conversation ID: ${conversationId}`);
    
    // Show typing indicator
    setIsTyping(true);
    
    // Remove the flight selection cards from the chat messages
    setMessages(prev => prev.filter(msg => !msg.isFlightSelection));

    // Clear flight options state
    setFlightOptions(null);
    
    try {
      // Add immediate feedback message
      setMessages(prev => [...prev, {
        id: Date.now() - 1,
        text: `Selected flight option ${flightIndex + 1}`,
        sender: 'user',
        timestamp: new Date()
      }]);
      
      // Process the selected flight using the backend
      console.log(`Calling selectFlight with index ${flightIndex}, conversationId ${conversationId}`);
      const flightResponse = await selectFlight(flightIndex, conversationId);
      console.log("Flight selection response:", flightResponse);
      
      // Add a message about the selected flight
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: flightResponse.message || `Flight selected. Continuing with your trip planning...`,
        sender: 'ai',
        timestamp: new Date()
      }]);
      
      // Check if we need to continue processing
      if (flightResponse.interaction_type === 'feedback' && flightResponse.data) {
        // We already have the complete itinerary, no need for continueProcessing
        
        // Add the itinerary message
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          text: formatItineraryText(flightResponse.data),
          sender: 'ai',
          timestamp: new Date(),
          hasItinerary: true
        }]);
        
        // Notify parent component with the itinerary data
        if (onSendMessage && typeof onSendMessage === 'function') {
          onSendMessage(JSON.stringify(flightResponse.data));
        }
      } else {
        // Add a message indicating we're continuing
        setMessages(prev => [...prev, {
          id: Date.now() + 1, 
          text: "Generating your complete itinerary...",
          sender: 'ai',
          timestamp: new Date(),
          isTemporary: true
        }]);
        
        // Continue processing to get the final itinerary
        console.log(`Calling continueProcessing with conversationId ${conversationId}`);
        const finalResponse = await continueProcessing(conversationId);
        console.log("Final itinerary response:", finalResponse);
        
        // Remove the temporary message
        setMessages(prev => prev.filter(msg => !msg.isTemporary));
        
        // Check if we got a valid itinerary data
        if (finalResponse.data?.itinerary || finalResponse.data?.daily_itinerary) {
          // Format and add the itinerary to chat
          setMessages(prev => [...prev, {
            id: Date.now() + 2,
            text: formatItineraryText(finalResponse.data),
            sender: 'ai',
            timestamp: new Date(),
            hasItinerary: true
          }]);
          
          // Notify parent component with the itinerary data
          if (onSendMessage && typeof onSendMessage === 'function') {
            onSendMessage(JSON.stringify(finalResponse.data));
          }
        } else if (finalResponse.error) {
          // Add the error message
          setMessages(prev => [...prev, {
            id: Date.now() + 2,
            text: `Error completing itinerary: ${finalResponse.error}`,
            sender: 'ai',
            timestamp: new Date()
          }]);
        } else {
          // Generic completion message
          setMessages(prev => [...prev, {
            id: Date.now() + 2,
            text: "Your trip has been planned, but no detailed itinerary could be generated.",
            sender: 'ai',
            timestamp: new Date()
          }]);
        }
      }
      
      // Hide typing indicator
      setIsTyping(false);
    } catch (error) {
      console.error('Error selecting flight:', error);
      
      // Add error message
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: `Sorry, there was an error processing your flight selection: ${error.message}. Please try again.`,
        sender: 'ai',
        timestamp: new Date()
      }]);
      
      // Hide typing indicator
      setIsTyping(false);
    }
  };
  
  // Helper function to format itinerary text from response data
  const formatItineraryText = (data) => {
    if (!data) return "No itinerary data available.";
    
    // Check various possible fields where itinerary might be
    if (data.daily_itinerary) {
      // Format daily itinerary
      return Object.keys(data.daily_itinerary).map(day => {
        const activities = Array.isArray(data.daily_itinerary[day]) 
          ? data.daily_itinerary[day] 
          : data.daily_itinerary[day].activities || [];
        
        return `Day ${day}:\n${activities.map(a => `- ${a.time || ''} ${a.activity || a.title || ''}`).join('\n')}`;
      }).join('\n\n');
    } else if (data.trip_summary) {
      // Format trip summary
      const summary = data.trip_summary;
      return `Trip to ${summary.destination} from ${summary.start_date} to ${summary.end_date}`;
    } else if (data.itinerary) {
      // Use provided itinerary string/object
      return typeof data.itinerary === 'string' 
        ? data.itinerary 
        : JSON.stringify(data.itinerary, null, 2);
    } else {
      // Generic message if no recognized format
      return "Your trip has been planned. You can view the details in the itinerary tab.";
    }
  };

  // Handle message sending
  const handleSendMessage = async () => {
    if (inputText.trim() === '') return;
    
    // Add user message to chat
    const userMessageText = inputText;
    const newUserMessage = {
      id: Date.now(),
      text: userMessageText,
      sender: 'user',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, newUserMessage]);
    setInputText('');
    
    // Show typing indicator
    setIsTyping(true);
    
    // Notify parent component to handle API call
    if (onSendMessage && typeof onSendMessage === 'function') {
      try {
        // Pass the message to parent - let parent handle API call
        onSendMessage(userMessageText);
      } catch (error) {
        console.error('Error in parent handler:', error);
        
        // Handle error locally if parent fails
        setIsTyping(false);
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          text: "Sorry, I'm having trouble processing your request. Please try again later.",
          sender: 'ai',
          timestamp: new Date()
        }]);
      }
    } else {
      // If no parent handler, show error
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: "Chat service is currently unavailable. Please try again later.",
        sender: 'ai',
        timestamp: new Date()
      }]);
    }
  };

  // Clean up when component unmounts
  useEffect(() => {
    return () => {
      // Stop any ongoing recording when component unmounts
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
    };
  }, []);

  // Process API response when it changes
  useEffect(() => {
    if (!apiResponse) return;
    
    console.log("Processing API response:", apiResponse);
    
    // Hide typing indicator
    setIsTyping(false);
    
    // Check if response is valid
    if (!apiResponse) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: "Sorry, I received an empty response from the server. Please try again.",
        sender: 'ai',
        timestamp: new Date()
      }]);
      return;
    }
    
    // Check if this is a flight selection request
    if (apiResponse.interaction_type === 'flight_selection' && apiResponse.data?.flights) {
      console.log(`Received flight options for selection`);
      
      // Store flight options in state
      setFlightOptions(apiResponse.data.flights);
      
      // First add a message asking to select flights
      setMessages(prev => [...prev, {
        id: Date.now() - 1,
        text: apiResponse.message || "Please select a flight that best suits your needs:",
        sender: 'ai',
        timestamp: new Date()
      }]);
      
      // Then add the flight selection UI to the chat
      setMessages(prev => [...prev, {
        id: Date.now(),
        isFlightSelection: true,
        flightOptions: apiResponse.data.flights,
        sender: 'ai',
        timestamp: new Date()
      }]);
      
      return;
    }
    
    // Handle legacy flight selection format
    if (apiResponse.selection_type === 'flight' && apiResponse.flight_options && apiResponse.flight_options.length > 0) {
      console.log(`Received ${apiResponse.flight_options.length} flight options (legacy format)`);
      
      // Store flight options in state
      setFlightOptions(apiResponse.flight_options);
      
      // First add a message asking to select flights
      setMessages(prev => [...prev, {
        id: Date.now() - 1,
        text: apiResponse.next_question || "Please select a flight that best suits your needs:",
        sender: 'ai',
        timestamp: new Date()
      }]);
      
      // Then add the flight selection UI to the chat
      setMessages(prev => [...prev, {
        id: Date.now(),
        isFlightSelection: true,
        flightOptions: apiResponse.flight_options,
        sender: 'ai',
        timestamp: new Date()
      }]);
      
      return;
    }
    
    // Check if feedback question exists and display it in the chat
    if (apiResponse.interaction_type === 'feedback' || apiResponse.feedback_question) {
      const feedbackText = apiResponse.message || apiResponse.feedback_question || "Would you like to modify anything in your itinerary?";
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: feedbackText,
        sender: 'ai',
        timestamp: new Date()
      }]);
    }
    
    // Prepare response text - handle complex objects
    let responseText = "";
    let hasItinerary = false;
    
    // First check if we have itinerary data in the response.data field
    if (apiResponse.data && (apiResponse.data.daily_itinerary || apiResponse.data.trip_summary || apiResponse.data.itinerary)) {
      responseText = formatItineraryText(apiResponse.data);
      hasItinerary = true;
    } else if (apiResponse.response) {
      if (typeof apiResponse.response === 'string') {
        // Try to parse JSON string responses
        try {
          const parsedResponse = JSON.parse(apiResponse.response);
          if (parsedResponse.daily_itinerary || parsedResponse.trip_summary) {
            // This is an itinerary - format it using our helper
            responseText = formatItineraryText(parsedResponse);
            hasItinerary = true;
          } else {
            // Just a regular JSON response
            responseText = JSON.stringify(parsedResponse, null, 2);
          }
        } catch (e) {
          // Not valid JSON, use as-is
          responseText = apiResponse.response;
        }
      } else {
        // It's already an object
        if (apiResponse.response.daily_itinerary || apiResponse.response.trip_summary) {
          responseText = formatItineraryText(apiResponse.response);
          hasItinerary = true;
        } else {
          // Fall back to JSON.stringify with formatting
          responseText = JSON.stringify(apiResponse.response, null, 2);
        }
      }
    } else if (apiResponse.itinerary) {
      responseText = typeof apiResponse.itinerary === 'string' 
        ? apiResponse.itinerary 
        : JSON.stringify(apiResponse.itinerary);
      hasItinerary = true;
    } else if (apiResponse.error) {
      responseText = `Error: ${apiResponse.error}`;
    } else if (apiResponse.message) {
      responseText = apiResponse.message;
    } else {
      responseText = "I couldn't process that request. Can you try again?";
    }
    
    // Add AI response to chat (only if not already handled)
    if (responseText) {
      const aiResponse = {
        id: Date.now() + 1,
        text: responseText,
        sender: 'ai',
        timestamp: new Date(),
        hasItinerary: hasItinerary
      };
      
      setMessages(prev => [...prev, aiResponse]);
    }
    
    // Update conversation ID if provided
    if (apiResponse.conversation_id) {
      setConversationId(apiResponse.conversation_id);
    }
  }, [apiResponse]);

  return (
    <div className="flex flex-col h-full">
      {/* Chat messages container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto bg-white"
      >
        <div>
          {messages.map((message, index) => (
            <div
              key={message.id}
              className={`px-4 py-6 ${message.sender === 'ai' ? 'bg-gray-50' : 'bg-white'} border-b border-gray-100`}
            >
              <div className="max-w-2xl mx-auto">
                {message.isFlightSelection ? (
                  <FlightSelection 
                    flights={message.flightOptions} 
                    onSelectFlight={handleFlightSelection}
                  />
                ) : (
                  <div className="flex">
                    <div className="w-7 h-7 rounded-full mr-4 flex-shrink-0">
                      {message.sender === 'ai' ? (
                        <div className="w-full h-full bg-black rounded-full flex items-center justify-center text-white text-xs font-medium">
                          TI
                        </div>
                      ) : (
                        <div className="w-full h-full bg-gray-600 rounded-full flex items-center justify-center text-white text-xs font-medium">
                          U
                        </div>
                      )}
                    </div>
                    <div className="flex-1">
                      <div className={`text-sm text-gray-800 ${message.isTemporary ? 'opacity-70' : ''} ${message.isRecording ? 'text-red-500 animate-pulse' : ''}`}>
                        <p className="whitespace-pre-line leading-relaxed">{message.text}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isTyping && (
            <div className="px-4 py-6 bg-gray-50 border-b border-gray-100">
              <div className="max-w-2xl mx-auto">
                <div className="flex">
                  <div className="w-7 h-7 rounded-full mr-4 flex-shrink-0">
                    <div className="w-full h-full bg-black rounded-full flex items-center justify-center text-white text-xs font-medium">
                      TI
                    </div>
                  </div>
                  <TypingIndicator />
                </div>
              </div>
            </div>
          )}
          
          <div ref={messageEndRef} className="h-2" />
        </div>
      </div>
      
      {/* Input area */}
      <div className="border-t border-gray-200 bg-white px-4 py-3">
        <div className="max-w-lg mx-auto">
          <div className="relative">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Message Travel Assistant..."
              className="w-full px-5 py-3 pr-24 border border-gray-300 rounded-full focus:outline-none focus:border-gray-400 focus:ring-0 resize-none"
              rows={1}
              style={{ 
                minHeight: '46px', 
                maxHeight: '200px' 
              }}
              disabled={isRecording}
            />
            
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center space-x-3">
              {isRecording ? (
                <button 
                  onClick={stopRecording}
                  className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-red-500 transition-colors"
                >
                  <FaStop className="text-sm" />
                </button>
              ) : (
                <button 
                  onClick={startRecording}
                  className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400 transition-colors"
                >
                  <FaMicrophone className="text-sm" />
                </button>
              )}
              
              <button 
                onClick={handleSendMessage}
                disabled={inputText.trim() === '' || isRecording}
                className={`w-9 h-9 flex items-center justify-center rounded-full ${
                  inputText.trim() === '' || isRecording 
                    ? 'text-gray-300' 
                    : 'text-white bg-black hover:bg-gray-800'
                } transition-colors`}
              >
                <FaPaperPlane className="text-xs" />
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <style jsx global>{`
        /* Custom typing indicator styles */
        .typing-dot {
          background-color: #333;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          animation: typingAnimation 1.4s infinite ease-in-out both;
        }
        
        .typing-dot:nth-child(1) {
          animation-delay: 0s;
        }
        
        .typing-dot:nth-child(2) {
          animation-delay: 0.2s;
        }
        
        .typing-dot:nth-child(3) {
          animation-delay: 0.4s;
        }
        
        @keyframes typingAnimation {
          0%, 100% {
            transform: scale(0.8);
            opacity: 0.6;
          }
          50% {
            transform: scale(1.2);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};

export default ChatInterface; 