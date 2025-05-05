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

const ChatInterface = ({ onSendMessage }) => {
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
      
      // If we're in step-by-step mode, continue to process the rest of the trip
      if (flightResponse.step_by_step && flightResponse.in_progress) {
        // Add a message to indicate we're continuing
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
        
        // Check if we got a valid itinerary
        if (finalResponse.itinerary) {
          // Add the final itinerary to the chat
          setMessages(prev => [...prev, {
            id: Date.now() + 2,
            text: finalResponse.itinerary,
            sender: 'ai',
            timestamp: new Date()
          }]);
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

  const handleSendMessage = async () => {
    if (inputText.trim() === '') return;
    
    // Add user message
    const newUserMessage = {
      id: Date.now(),
      text: inputText,
      sender: 'user',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, newUserMessage]);
    const userMessageText = inputText;
    setInputText('');
    
    // Notify parent component
    onSendMessage(userMessageText);
    
    // Show typing indicator
    setIsTyping(true);
    
    try {
      // Ensure we have a conversation ID
      if (!conversationId) {
        // Try to create one if missing
        try {
          const convResponse = await createConversation();
          if (convResponse && convResponse.conversation_id) {
            setConversationId(convResponse.conversation_id);
          }
        } catch (convError) {
          console.error('Error creating conversation on demand:', convError);
        }
      }
      
      console.log('Sending message with conversation ID:', conversationId);
      
      // Send message to backend
      const response = await sendChatMessage(userMessageText, conversationId);
      console.log("Response from sendChatMessage:", response);
      
      // Hide typing indicator
      setIsTyping(false);
      
      // Check if this is a flight selection request
      if (response.selection_type === 'flight' && response.flight_options && response.flight_options.length > 0) {
        console.log(`Received ${response.flight_options.length} flight options`);
        
        // Store flight options in state
        setFlightOptions(response.flight_options);
        
        // First add a message asking to select flights
        setMessages(prev => [...prev, {
          id: Date.now() - 1,
          text: response.next_question || "Please select a flight that best suits your needs:",
          sender: 'ai',
          timestamp: new Date()
        }]);
        
        // Then add the flight selection UI to the chat
        setMessages(prev => [...prev, {
          id: Date.now(),
          isFlightSelection: true,
          flightOptions: response.flight_options,
          sender: 'ai',
          timestamp: new Date()
        }]);
        
        return;
      }
      
      // Check if feedback question exists and display it in the chat
      if (response.feedback_question) {
        setMessages(prev => [...prev, {
          id: Date.now(),
          text: response.feedback_question,
          sender: 'ai',
          timestamp: new Date()
        }]);
      }
      
      // Prepare response text - handle complex objects
      let responseText = "";
      let hasItinerary = false;
      
      if (response.response) {
        if (typeof response.response === 'string') {
          // Try to parse JSON string responses
          try {
            const parsedResponse = JSON.parse(response.response);
            if (parsedResponse.daily_itinerary || parsedResponse.trip_summary) {
              // This is an itinerary - format it for the chat
              if (parsedResponse.daily_itinerary) {
                const dailyItinerary = parsedResponse.daily_itinerary;
                // Format itinerary days
                responseText = Object.keys(dailyItinerary).map(day => {
                  const activities = dailyItinerary[day];
                  return `Day ${day}:\n${activities.map(a => `- ${a.time || ''} ${a.activity || a.title || ''}`).join('\n')}`;
                }).join('\n\n');
              } else if (parsedResponse.trip_summary) {
                // Format trip summary
                const summary = parsedResponse.trip_summary;
                responseText = `Trip to ${summary.destination} from ${summary.start_date} to ${summary.end_date}`;
              }
              hasItinerary = true;
            } else {
              // Just a regular JSON response
              responseText = JSON.stringify(parsedResponse, null, 2);
            }
          } catch (e) {
            // Not valid JSON, use as-is
            responseText = response.response;
          }
        } else {
          // It's already an object
          if (response.response.daily_itinerary) {
            const dailyItinerary = response.response.daily_itinerary;
            // Format itinerary days
            responseText = Object.keys(dailyItinerary).map(day => {
              const activities = Array.isArray(dailyItinerary[day]) 
                ? dailyItinerary[day] 
                : dailyItinerary[day].activities || [];
              
              return `Day ${day}:\n${activities.map(a => `- ${a.time || ''} ${a.activity || a.title || ''}`).join('\n')}`;
            }).join('\n\n');
            hasItinerary = true;
          } else if (response.response.trip_summary) {
            // Format trip summary
            const summary = response.response.trip_summary;
            responseText = `Trip to ${summary.destination} from ${summary.start_date} to ${summary.end_date}`;
            hasItinerary = true;
          } else {
            // Fall back to JSON.stringify with formatting
            responseText = JSON.stringify(response.response, null, 2);
          }
        }
      } else if (response.itinerary) {
        responseText = typeof response.itinerary === 'string' 
          ? response.itinerary 
          : JSON.stringify(response.itinerary);
        hasItinerary = true;
      } else if (response.error) {
        responseText = `Error: ${response.error}`;
      } else if (response.message) {
        responseText = response.message;
      } else if (response.result) {
        // Handle 'result' field which might contain the itinerary
        if (typeof response.result === 'string') {
          responseText = response.result;
        } else {
          responseText = JSON.stringify(response.result, null, 2);
        }
        hasItinerary = true;
      } else {
        responseText = "I couldn't process that request. Can you try again?";
      }
      
      // Add AI response to chat
      const aiResponse = {
        id: Date.now() + 1,
        text: responseText,
        sender: 'ai',
        timestamp: new Date(),
        hasItinerary: hasItinerary
      };
      
      setMessages(prev => [...prev, aiResponse]);
      
      // Update conversation ID if provided
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Hide typing indicator
      setIsTyping(false);
      
      // Add error message
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: "Sorry, I'm having trouble connecting to the server. Please try again later.",
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