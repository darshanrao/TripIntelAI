import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FaMicrophone, FaPaperPlane, FaStop } from 'react-icons/fa';
import { sendChatMessage, createConversation } from '../services/api';

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
  const recognitionRef = useRef(null);

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

  // Speech recognition implementation
  const startRecording = () => {
    if (isRecording) return;
    
    if (window.SpeechRecognition || window.webkitSpeechRecognition) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'en-US';
      
      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0])
          .map(result => result.transcript)
          .join('');
        
        setInputText(transcript);
      };
      
      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error', event);
        setIsRecording(false);
      };
      
      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };
      
      recognitionRef.current.start();
      setIsRecording(true);
    } else {
      alert('Speech recognition is not supported in your browser.');
    }
  };

  const stopRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsRecording(false);
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
      
      // Add AI response to chat
      const aiResponse = {
        id: Date.now() + 1,
        text: response.itinerary || response.error || "I couldn't process that request. Can you try again?",
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
          >
            <FaPaperPlane />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface; 