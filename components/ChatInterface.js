import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FaMicrophone, FaPaperPlane, FaStop } from 'react-icons/fa';
import { sendChatMessage, createConversation, saveAndProcessAudio } from '../services/api';

const TypingIndicator = () => (
  <div className="flex items-center space-x-1 p-3 ml-2 bg-chat-ai rounded-lg max-w-xs shadow-sm typing-dots">
    <span className="h-2 w-2 bg-gray-400 rounded-full"></span>
    <span className="h-2 w-2 bg-gray-400 rounded-full"></span>
    <span className="h-2 w-2 bg-gray-400 rounded-full"></span>
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
        setConversationId(response.conversation_id);
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
      // Send message to backend
      const response = await sendChatMessage(userMessageText, conversationId);
      
      // Hide typing indicator
      setIsTyping(false);
      
      // Prepare response text - handle complex objects
      let responseText = "";
      if (response.response) {
        if (typeof response.response === 'string') {
          responseText = response.response;
        } else {
          // It's an object, convert to readable text
          try {
            if (response.response.daily_itinerary) {
              const dailyItinerary = response.response.daily_itinerary;
              // Format itinerary days
              responseText = Object.keys(dailyItinerary).map(day => {
                const activities = dailyItinerary[day];
                return `Day ${day}:\n${activities.map(a => `- ${a.time || ''} ${a.activity}`).join('\n')}`;
              }).join('\n\n');
            } else if (response.response.trip_summary) {
              // Format trip summary
              const summary = response.response.trip_summary;
              responseText = `Trip to ${summary.destination} from ${summary.start_date} to ${summary.end_date}`;
            } else {
              // Fall back to JSON.stringify with formatting
              responseText = JSON.stringify(response.response, null, 2);
            }
          } catch (error) {
            // If we can't process it nicely, fall back to simple stringify
            responseText = JSON.stringify(response.response);
          }
        }
      } else if (response.itinerary) {
        responseText = typeof response.itinerary === 'string' 
          ? response.itinerary 
          : JSON.stringify(response.itinerary);
      } else if (response.error) {
        responseText = response.error;
      } else {
        responseText = "I couldn't process that request. Can you try again?";
      }
      
      // Add AI response to chat
      const aiResponse = {
        id: Date.now() + 1,
        text: responseText,
        sender: 'ai',
        timestamp: new Date()
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
    <div className="flex flex-col h-full bg-gray-50">
      {/* Chat header */}
      <div className="bg-primary p-4 text-white shadow-sm">
        <h2 className="text-xl font-semibold">Travel Assistant</h2>
      </div>
      
      {/* Messages container */}
      <div 
        ref={chatContainerRef}
        className="flex-1 p-4 overflow-y-auto"
      >
        <div className="space-y-4">
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div 
                className={`
                  max-w-xs rounded-lg p-3 shadow-sm chat-bubble
                  ${message.sender === 'user' 
                    ? 'bg-primary text-white rounded-br-none' 
                    : 'bg-chat-ai rounded-bl-none'
                  }
                  ${message.isTemporary ? 'opacity-60' : ''}
                  ${message.isRecording ? 'animate-pulse' : ''}
                `}
              >
                <p className="text-sm">{message.text}</p>
                <p className="text-xs mt-1 opacity-70">
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </motion.div>
          ))}
          
          {isTyping && (
            <div className="flex justify-start">
              <TypingIndicator />
            </div>
          )}
          
          <div ref={messageEndRef} />
        </div>
      </div>
      
      {/* Input area */}
      <div className="border-t border-gray-200 p-3 bg-white">
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type your message..."
            className="flex-1 rounded-full border border-gray-300 py-2 px-4 focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={isRecording}
          />
          
          {isRecording ? (
            <button 
              onClick={stopRecording}
              className="bg-red-500 text-white p-3 rounded-full shadow-md hover:bg-red-600 transition-colors"
            >
              <FaStop />
            </button>
          ) : (
            <button 
              onClick={startRecording}
              className="bg-gray-200 text-gray-600 p-3 rounded-full shadow-md hover:bg-gray-300 transition-colors"
            >
              <FaMicrophone />
            </button>
          )}
          
          <button 
            onClick={handleSendMessage}
            className="bg-primary text-white p-3 rounded-full shadow-md hover:bg-blue-600 transition-colors"
            disabled={isRecording}
          >
            <FaPaperPlane />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface; 