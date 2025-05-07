import { useState, useRef, useEffect } from 'react';
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FaMicrophone, FaPaperPlane, FaStop } from 'react-icons/fa';
import { sendChatMessage, createConversation, saveAndProcessAudio, selectFlight, continueProcessing, searchFlights } from '../services/api';
import tripPlannerWebSocket from '../services/websocket';
import FlightSelection from './FlightSelection';

const TypingIndicator = () => (
  <div className="flex items-center space-x-1 py-1">
    <div className="typing-dot"></div>
    <div className="typing-dot"></div>
    <div className="typing-dot"></div>
  </div>
);

const ItineraryMessage = ({ data }) => {
  if (!data || !data.trip_summary) return null;
  
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 my-2">
      <h3 className="font-semibold text-lg mb-2">Trip Summary</h3>
      <div className="text-sm text-gray-700">
        <p><span className="font-medium">Destination:</span> {data.trip_summary.destination}</p>
        <p><span className="font-medium">Dates:</span> {data.trip_summary.start_date} to {data.trip_summary.end_date}</p>
        <p><span className="font-medium">Duration:</span> {data.trip_summary.duration_days} days</p>
        <p><span className="font-medium">Total Budget:</span> ${data.trip_summary.total_budget?.toFixed(2)}</p>
      </div>
      
      {data.daily_itinerary && Object.entries(data.daily_itinerary).map(([day, dayData]) => (
        <div key={day} className="mt-4">
          <h4 className="font-medium text-md">{day.replace('_', ' ').toUpperCase()}</h4>
          <div className="ml-4">
            {dayData.activities?.map((activity, idx) => (
              <div key={idx} className="my-2">
                <p className="text-sm">
                  <span className="font-medium">{activity.time}:</span> {activity.title}
                </p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

const ChatInterface = ({ onSendMessage, apiResponse }) => {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hi there! I'm your AI travel assistant. Where would you like to go?", sender: 'ai', timestamp: new Date() }
  ]);
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [flightOptions, setFlightOptions] = useState(null);
  const [returnFlightOptions, setReturnFlightOptions] = useState(null);
  const [selectedDepartureFlight, setSelectedDepartureFlight] = useState(null);
  const [isFirstUserMessage, setIsFirstUserMessage] = useState(true);
  const [isSearchingFlights, setIsSearchingFlights] = useState(false);
  const [flightSelectionStep, setFlightSelectionStep] = useState('outbound');
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
          
          // Check if this is the first user message
          const firstMessage = isFirstUserMessage;
          if (isFirstUserMessage) {
            setIsFirstUserMessage(false);
            
            // Process the audio first to get the transcript
            const transcriptResponse = await saveAndProcessAudio(audioBlob);
            
            // Remove the processing message
            setMessages(prev => prev.filter(msg => !msg.isTemporary));
            
            if (!transcriptResponse.success || !transcriptResponse.transcript) {
              setMessages(prev => [...prev, {
                id: Date.now() + 1,
                text: "I couldn't understand your audio. Please try speaking clearly or typing your message.",
                sender: 'ai',
                timestamp: new Date()
              }]);
              setIsTyping(false);
              return;
            }
            
            // Display what we heard
            setMessages(prev => [...prev, {
              id: Date.now(),
              text: `I heard: "${transcriptResponse.transcript}"`,
              sender: 'ai',
              timestamp: new Date(),
              isTranscript: true
            }]);
            
            // For the first message, initiate flight search process
            try {
              // Add flight search message
              setMessages(prev => [...prev, {
                id: Date.now() + 1,
                text: "Searching for flight options based on your request...",
                sender: 'ai',
                timestamp: new Date()
              }]);
              
              setIsSearchingFlights(true);
              
              // First call the dedicated flight search endpoint
              const searchResponse = await searchFlights(transcriptResponse.transcript, conversationId);
              console.log("Flight search response:", searchResponse);
              
              if (searchResponse.error) {
                setMessages(prev => [...prev, {
                  id: Date.now() + 2,
                  text: `Error searching flights: ${searchResponse.error}`,
                  sender: 'ai',
                  timestamp: new Date()
                }]);
                setIsTyping(false);
                setIsSearchingFlights(false);
                return;
              }
              
              // Now send the regular message to get flight options
              if (onSendMessage && typeof onSendMessage === 'function') {
                onSendMessage(transcriptResponse.transcript, { 
                  requestFlightOptions: true,
                  searchResults: searchResponse.search_id || searchResponse.id
                });
              }
            } catch (error) {
              console.error("Error during flight search:", error);
              setMessages(prev => [...prev, {
                id: Date.now() + 2,
                text: `Error searching flights: ${error.message}. Please try again with more specific details.`,
                sender: 'ai',
                timestamp: new Date()
              }]);
              setIsTyping(false);
              setIsSearchingFlights(false);
            }
          } else {
            // Not the first message, process audio normally
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
                timestamp: new Date(),
                data: response.data
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
          }
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
  const handleFlightSelection = async (flightIdOrIndex) => {
    if (!conversationId) {
      console.error('No conversation ID available');
      return;
    }
    
    // Check if we're selecting an outbound or return flight
    if (flightSelectionStep === 'outbound') {
      // Selecting outbound flight
      console.log(`Selected outbound flight: ${flightIdOrIndex}, conversation ID: ${conversationId}`);
      
      // Store flight options before clearing
      const currentFlightOptions = flightOptions;
      
      // Find the selected flight
      let selectedFlight;
      if (typeof flightIdOrIndex === 'string' && currentFlightOptions) {
        // If it's a string, it's the flight ID
        selectedFlight = currentFlightOptions.find(f => f.id === flightIdOrIndex);
      } else if (currentFlightOptions) {
        // Otherwise it's the index
        selectedFlight = currentFlightOptions[flightIdOrIndex];
      }
      
      // Store the selected departure flight
      setSelectedDepartureFlight(selectedFlight);
      
      // Add a message about the selected flight
      if (selectedFlight) {
        setMessages(prev => [...prev, {
          id: Date.now() - 1,
          text: `Selected ${selectedFlight.airline} flight ${selectedFlight.flight_number} to ${selectedFlight.arrival_city} for your outbound journey`,
          sender: 'user',
          timestamp: new Date()
        }]);
      } else {
        setMessages(prev => [...prev, {
          id: Date.now() - 1,
          text: `Selected outbound flight option ${flightIdOrIndex + 1}`,
          sender: 'user',
          timestamp: new Date()
        }]);
      }
      
      // Change to return flight selection step
      setFlightSelectionStep('return');
      
      // Remove the outbound flight selection cards from the chat messages
      setMessages(prev => prev.filter(msg => !msg.isFlightSelection));
      
      // Create return flight options (in real app, these would come from the API)
      const returnFlights = currentFlightOptions.map((flight, index) => ({
        ...flight,
        id: `ret-${index}`,
        flight_type: 'return',
        // Swap departure and arrival for return flights
        departure_city: flight.arrival_city,
        arrival_city: flight.departure_city,
        departure_airport: flight.arrival_airport,
        arrival_airport: flight.departure_airport
      }));
      
      // Store return flight options
      setReturnFlightOptions(returnFlights);
      
      // Show the return flight selection message and options
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: "Now please select your return flight:",
        sender: 'ai',
        timestamp: new Date()
      }]);
      
      // Add the return flight selection UI to the chat
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        isFlightSelection: true,
        flightOptions: returnFlights,
        sender: 'ai',
        timestamp: new Date()
      }]);
      
    } else {
      // Selecting return flight
      console.log(`Selected return flight: ${flightIdOrIndex}, conversation ID: ${conversationId}`);
      
      // Show typing indicator
      setIsTyping(true);
      
      // Remove the flight selection cards from the chat messages
      setMessages(prev => prev.filter(msg => !msg.isFlightSelection));
      
      // Find the selected return flight
      let selectedReturnFlight;
      if (typeof flightIdOrIndex === 'string' && returnFlightOptions) {
        // If it's a string, it's the flight ID
        selectedReturnFlight = returnFlightOptions.find(f => f.id === flightIdOrIndex);
      } else if (returnFlightOptions) {
        // Otherwise it's the index
        selectedReturnFlight = returnFlightOptions[flightIdOrIndex];
      }
      
      // Add a message about the selected return flight
      if (selectedReturnFlight) {
        setMessages(prev => [...prev, {
          id: Date.now() - 1,
          text: `Selected ${selectedReturnFlight.airline} flight ${selectedReturnFlight.flight_number} to ${selectedReturnFlight.arrival_city} for your return journey`,
          sender: 'user',
          timestamp: new Date()
        }]);
      } else {
        setMessages(prev => [...prev, {
          id: Date.now() - 1,
          text: `Selected return flight option ${flightIdOrIndex + 1}`,
          sender: 'user',
          timestamp: new Date()
        }]);
      }
      
      // Clear flight options state
      setFlightOptions(null);
      setReturnFlightOptions(null);
      
      try {
        // Process both selected flights using the backend
        console.log(`Calling selectFlight with outbound ID ${selectedDepartureFlight?.id || 'dep-0'} and return ID ${flightIdOrIndex}, conversationId ${conversationId}`);
        
        // Call the API with both flight selections
        const flightResponse = await selectFlight(flightIdOrIndex, conversationId, selectedDepartureFlight?.id || 'dep-0');
        console.log("Flight selection response:", flightResponse);
        
        // Add a message about the selected flights
        setMessages(prev => [...prev, {
          id: Date.now(),
          text: flightResponse.message || `Flights selected. Continuing with your trip planning...`,
          sender: 'ai',
          timestamp: new Date()
        }]);
        
        // Reset the flight selection step for next time
        setFlightSelectionStep('outbound');
        
        // Check if we need to continue processing
        if (flightResponse.interaction_type === 'feedback' && flightResponse.data) {
          // We already have the complete itinerary, no need for continueProcessing
          
          // Add the itinerary message
          setMessages(prev => [...prev, {
            id: Date.now() + 1,
            text: "Your itinerary has been updated with your flight selection.",
            sender: 'ai',
            timestamp: new Date(),
            hasItinerary: true
          }]);
          
          // Notify parent component with the itinerary data
          if (onSendMessage && typeof onSendMessage === 'function') {
            onSendMessage(JSON.stringify(flightResponse.data));
          }
        } else {
          // We need to continue processing to get the final itinerary
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
            // Add a message about the itinerary update
            setMessages(prev => [...prev, {
              id: Date.now() + 2,
              text: "Your itinerary has been generated. Check the itinerary view for details.",
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
        console.error('Error selecting flights:', error);
        
        // Add error message
        setMessages(prev => [...prev, {
          id: Date.now(),
          text: `Sorry, there was an error processing your flight selection: ${error.message}. Please try again.`,
          sender: 'ai',
          timestamp: new Date()
        }]);
        
        // Hide typing indicator
        setIsTyping(false);
        
        // Reset flight selection step
        setFlightSelectionStep('outbound');
      }
    }
  };
  
  // Helper function to format itinerary text from response data
  const formatItineraryText = (data) => {
    if (!data) return "No itinerary data available.";
    
    let text = "";
    
    // Format trip summary
    if (data.trip_summary) {
      text += "Trip Summary:\n";
      text += `- Destination: ${data.trip_summary.destination || 'Not specified'}\n`;
      text += `- Dates: ${data.trip_summary.start_date || 'Not specified'} to ${data.trip_summary.end_date || 'Not specified'}`;
      if (data.trip_summary.duration_days) {
        text += ` (${data.trip_summary.duration_days} days)`;
      }
      text += '\n';
      if (data.trip_summary.total_budget) {
        text += `- Total Budget: $${data.trip_summary.total_budget.toFixed(2)}\n`;
      }
      text += "\n";
    }
    
    // Format daily itinerary
    if (data.daily_itinerary) {
      text += "Daily Itinerary:\n\n";
      Object.entries(data.daily_itinerary).forEach(([day, dayData]) => {
        if (!dayData) return; // Skip if no data for this day
        
        text += `${day.replace('_', ' ').toUpperCase()}`;
        if (dayData.date) {
          text += ` (${dayData.date})`;
        }
        text += ':\n';
        
        if (dayData.activities && dayData.activities.length > 0) {
          dayData.activities.forEach((activity, index) => {
            if (!activity) return; // Skip if activity is null
            
            text += `${index + 1}. ${activity.time || ''} - ${activity.title || ''}`;
            
            if (activity.duration_minutes) {
              const hours = Math.floor(activity.duration_minutes / 60);
              const minutes = activity.duration_minutes % 60;
              if (hours > 0 || minutes > 0) {
                text += ` (${hours > 0 ? `${hours} hours` : ''}${minutes > 0 ? ` ${minutes} minutes` : ''})`;
              }
            }
            
            if (activity.details) {
              if (activity.details.location) {
                text += `\n   Location: ${activity.details.location}`;
              }
              if (activity.details.airline) {
                text += `\n   Airline: ${activity.details.airline} ${activity.details.flight_number || ''}`;
                if (activity.details.arrival_time) {
                  text += `, arrives ${activity.details.arrival_time}`;
                }
              }
            }
            
            if (activity.review_insights) {
              if (activity.review_insights.strengths && activity.review_insights.strengths.length > 0) {
                text += `\n   Highlights: ${activity.review_insights.strengths.join(", ")}`;
              }
            }
            
            text += "\n\n";
          });
        }
      });
    }
    
    // Format hotel review summary
    if (data.review_highlights?.hotel_review_summary) {
      const hotel = data.review_highlights.hotel_review_summary;
      text += "Hotel Details:\n";
      text += `${hotel.name || 'Hotel name not specified'}\n`;
      if (hotel.rating) {
        text += `- Rating: ${hotel.rating}/5\n`;
      }
      if (hotel.strengths && hotel.strengths.length > 0) {
        text += "- Highlights:\n";
        hotel.strengths.forEach(strength => {
          text += `  • ${strength}\n`;
        });
      }
      if (hotel.weaknesses && hotel.weaknesses.length > 0) {
        text += "- Note:\n";
        hotel.weaknesses.forEach(weakness => {
          text += `  • ${weakness}\n`;
        });
      }
      if (hotel.summary) {
        text += `\nSummary: ${hotel.summary}\n`;
      }
      text += "\n";
    }
    
    // Add modification options
    text += "Would you like to modify anything? You can adjust:\n";
    text += "1. Transportation (flights/routes)\n";
    text += "2. Accommodations (hotel selection)\n";
    text += "3. Activities (places to visit)\n";
    text += "4. Dining options (restaurants)\n";
    text += "5. Schedule (timing of activities)\n";
    text += "6. Budget\n";
    
    return text;
  };

  // Handle message sending
  const handleSendMessage = async () => {
    if (!inputText.trim() && !isRecording) return;
    
    const userMessage = {
      id: Date.now(),
      text: inputText,
      sender: 'user',
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    
    // Save current input before clearing
    const messageToSend = inputText;
    
    // Clear input and show typing indicator
    setInputText('');
    setIsTyping(true);
    
    // Check if this is the first user message
    const firstMessage = isFirstUserMessage;
    if (isFirstUserMessage) {
      setIsFirstUserMessage(false);
      
      // For the first message, initiate flight search process
      try {
        // Add flight search message
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          text: "Searching for flight options based on your request...",
          sender: 'ai',
          timestamp: new Date()
        }]);
        
        setIsSearchingFlights(true);
        
        // First call the dedicated flight search endpoint
        const searchResponse = await searchFlights(messageToSend, conversationId);
        console.log("Flight search response:", searchResponse);
        
        if (searchResponse.error) {
          setMessages(prev => [...prev, {
            id: Date.now() + 2,
            text: `Error searching flights: ${searchResponse.error}`,
            sender: 'ai',
            timestamp: new Date()
          }]);
          setIsTyping(false);
          setIsSearchingFlights(false);
          return;
        }
        
        // Now send the regular message to get flight options
        if (onSendMessage && typeof onSendMessage === 'function') {
          onSendMessage(messageToSend, { 
            requestFlightOptions: true,
            searchResults: searchResponse.search_id || searchResponse.id
          });
        }
      } catch (error) {
        console.error("Error during flight search:", error);
        setMessages(prev => [...prev, {
          id: Date.now() + 2,
          text: `Error searching flights: ${error.message}. Please try again with more specific details.`,
          sender: 'ai',
          timestamp: new Date()
        }]);
        setIsTyping(false);
        setIsSearchingFlights(false);
      }
    } else {
      // Not the first message, proceed normally
      if (onSendMessage && typeof onSendMessage === 'function') {
        onSendMessage(messageToSend);
      } else {
        console.warn('onSendMessage not provided or not a function');
        setIsTyping(false);
      }
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
    
    // Hide typing indicator and flight search indicator
    setIsTyping(false);
    setIsSearchingFlights(false);
    
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
      console.log(`Received flight options for selection`, apiResponse.data.flights);
      
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
      
      // Get the itinerary data from the correct location
      const itineraryData = apiResponse.data?.itinerary || {};
      
      // Add just the feedback message, not the itinerary details
      setMessages(prev => [...prev, {
        id: Date.now(),
        text: feedbackText,
        sender: 'ai',
        timestamp: new Date(),
        hasItinerary: true
      }]);
      
      // Notify parent component with the itinerary data
      if (onSendMessage && typeof onSendMessage === 'function') {
        onSendMessage(JSON.stringify(itineraryData));
      }
      
      // Early return to prevent duplicate messages
      return;
    }
    
    // Handle other types of responses
    let responseText = "";
    let hasItinerary = false;
    
    if (apiResponse.data?.itinerary) {
      // Access the nested itinerary data
      responseText = formatItineraryText(apiResponse.data.itinerary);
      hasItinerary = true;
    } else if (apiResponse.response) {
      if (typeof apiResponse.response === 'string') {
        try {
          const parsedResponse = JSON.parse(apiResponse.response);
            responseText = formatItineraryText(parsedResponse);
            hasItinerary = true;
        } catch (e) {
          responseText = apiResponse.response;
        }
      } else {
          responseText = formatItineraryText(apiResponse.response);
          hasItinerary = true;
      }
    } else if (apiResponse.error) {
      responseText = `Error: ${apiResponse.error}`;
    } else if (apiResponse.message) {
      responseText = apiResponse.message;
    } else {
      responseText = "I couldn't process that request. Can you try again?";
    }
    
    // Add the response to chat if we have text and haven't handled it already
    if (responseText) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: responseText,
        sender: 'ai',
        timestamp: new Date(),
        hasItinerary: hasItinerary
      }]);
    }
    
    // Update conversation ID if provided
    if (apiResponse.conversation_id) {
      setConversationId(apiResponse.conversation_id);
    }
  }, [apiResponse]);

  // Modify the message rendering in the chat container
  const renderMessage = (message) => {
    // If this is a flight selection message, render the flight selection component
    if (message.isFlightSelection && message.flightOptions) {
      return (
        <div className="w-full my-2">
          <FlightSelection 
            flights={message.flightOptions} 
            onSelectFlight={handleFlightSelection}
            flightType={flightSelectionStep === 'outbound' ? 'Outbound' : 'Return'}
          />
        </div>
      );
    }
    
    // Skip rendering itinerary content in the chat
    if (message.hasItinerary) {
      return (
        <motion.div
          key={message.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
        >
          <div className={`rounded-lg px-4 py-2 max-w-[80%] ${
            message.sender === 'user' ? 'bg-primary text-white' : 'bg-gray-100'
          }`}>
            <div className="text-sm whitespace-pre-wrap">
              Your itinerary has been updated. Check the itinerary view to see the details.
            </div>
          </div>
        </motion.div>
      );
    }
    
    // Regular message rendering
    return (
      <motion.div
        key={message.id}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div className={`rounded-lg px-4 py-2 max-w-[80%] ${
          message.sender === 'user' ? 'bg-primary text-white' : 'bg-gray-100'
        }`}>
          <div className="text-sm whitespace-pre-wrap">{message.text}</div>
        </div>
      </motion.div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat messages container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        {messages.map((message) => (
          <React.Fragment key={message.id}>
            {renderMessage(message)}
          </React.Fragment>
        ))}
        
        {/* Typing indicator */}
        {isTyping && (
        <div className="flex justify-start mb-4">
          <div className="bg-gray-100 rounded-lg px-4 py-2">
                <TypingIndicator />
              </div>
            </div>
        )}
        
        {/* Flight Search Loading Indicator */}
        {isSearchingFlights && (
        <div className="flex justify-start mb-4">
          <div className="bg-gray-100 rounded-lg px-4 py-3">
            <div className="flex items-center">
              <div className="w-4 h-4 mr-3 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm">Searching for flights...</span>
            </div>
          </div>
        </div>
        )}
        
        {/* Message end ref for auto-scrolling */}
        <div ref={messageEndRef} />
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