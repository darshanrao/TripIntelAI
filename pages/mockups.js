import { useState, useEffect } from 'react';
import Head from 'next/head';
import ChatInterface from '../components/ChatInterface';
import ItineraryView from '../components/ItineraryView';
import MapView from '../components/MapView';
import { motion } from 'framer-motion';
import * as mockApi from '../services/mockApi';
import { mockItineraryData } from '../services/mockData';

export default function MockupsPage() {
  const [selectedDay, setSelectedDay] = useState(1);
  const [itineraryData, setItineraryData] = useState(null);
  const [isMobile, setIsMobile] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [isLoading, setIsLoading] = useState(false);
  const [apiResponse, setApiResponse] = useState(null);

  useEffect(() => {
    // Check if the screen is mobile
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    // Add window resize listener
    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    
    // Set mock itinerary data initially
    setItineraryData(mockItineraryData);
    
    // Initialize with a mock API response
    setApiResponse({
      success: true,
      response: "Welcome to the TripIntel mockup! You can test the chat interface and itinerary view with mock data.",
      data: mockItineraryData
    });
    
    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  // Process API response when it changes
  useEffect(() => {
    if (!apiResponse) return;
    
    console.log("Processing API response in Mockups:", apiResponse);
    
    try {
      // Process itinerary data for both chat and itinerary views
      if (apiResponse.data?.daily_itinerary) {
        processItineraryResponse(apiResponse.data);
      } else if (apiResponse.response) {
        if (typeof apiResponse.response === 'string') {
          try {
            const parsedResponse = JSON.parse(apiResponse.response);
            processItineraryResponse(parsedResponse);
          } catch (e) {
            console.log('Response not in JSON format, skipping parse');
          }
        } else {
          processItineraryResponse(apiResponse.response);
        }
      } else if (apiResponse.itinerary && typeof apiResponse.itinerary === 'object') {
        processItineraryResponse(apiResponse.itinerary);
      }
      
      // If on mobile, switch to itinerary view when we have data
      if (isMobile && itineraryData) {
        setActiveTab('itinerary');
      }
    } catch (error) {
      console.error('Error processing API response:', error);
    }
  }, [apiResponse]);

  const handleChatMessage = async (message) => {
    console.log('Message from chat:', message);
    
    if (!message || message.trim() === '') {
      console.error('Empty message detected');
      return;
    }
    
    setIsLoading(true);
    
    try {
      // Call the mock API instead of the real API
      const response = await mockApi.sendChatMessage(message);
      console.log('Mock API response:', response);
      
      // Store the API response
      setApiResponse(response);
      
      if (response.error) {
        console.error('API returned an error:', response.error);
      }
    } catch (error) {
      console.error('Error processing message:', error);
      
      // Set error response
      setApiResponse({
        error: error.message,
        message: "Sorry, there was an error processing your request."
      });
    } finally {
      setIsLoading(false);
    }
  };

  const processItineraryResponse = (response) => {
    console.log("Processing itinerary response:", response);
    
    if (!response) {
      console.error('Empty response received');
      return;
    }

    try {
      // Transform the data into the expected format for both views
      const processedData = {
        trip_summary: response.trip_summary || null,
        daily_itinerary: response.daily_itinerary || {},
        review_highlights: response.review_highlights || null,
        flights: response.flights || []
      };
      
      console.log("Processed itinerary data:", processedData);
      setItineraryData(processedData);
    } catch (error) {
      console.error('Error processing itinerary data:', error);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <Head>
        <title>TripIntel - Mockups</title>
        <meta name="description" content="TripIntel mockup page" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Development Header Banner */}
      <div className="bg-yellow-500 text-black py-2 px-4 text-center font-semibold">
        Mockup Mode - Using Dummy Data
      </div>

      {/* Mobile Navigation */}
      {isMobile && (
        <div className="flex border-b border-gray-200">
          <button 
            className={`flex-1 py-3 text-center ${activeTab === 'chat' ? 'bg-primary text-white' : 'bg-gray-100'}`}
            onClick={() => setActiveTab('chat')}
          >
            Chat
          </button>
          <button 
            className={`flex-1 py-3 text-center ${activeTab === 'itinerary' ? 'bg-primary text-white' : 'bg-gray-100'}`}
            onClick={() => setActiveTab('itinerary')}
          >
            Itinerary
          </button>
          <button 
            className={`flex-1 py-3 text-center ${activeTab === 'map' ? 'bg-primary text-white' : 'bg-gray-100'}`}
            onClick={() => setActiveTab('map')}
          >
            Map
          </button>
        </div>
      )}

      {/* Loading Overlay */}
      {isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-xl flex flex-col items-center">
            <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-700">Processing your request...</p>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className={`flex ${isMobile ? 'flex-col' : 'flex-row'} flex-1 overflow-hidden`}>
        {/* Left Column - Chat Interface */}
        <motion.div 
          className={`${isMobile ? (activeTab === 'chat' ? 'flex-1' : 'hidden') : 'w-1/3 border-r'} flex flex-col`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <ChatInterface 
            onSendMessage={handleChatMessage} 
            apiResponse={apiResponse}
          />
        </motion.div>
        
        {/* Right Column - Itinerary View */}
        <motion.div 
          className={`${isMobile ? (activeTab === 'itinerary' ? 'flex-1' : 'hidden') : 'w-2/3'} flex flex-col overflow-hidden`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <ItineraryView 
            itineraryData={itineraryData} 
            apiResponse={apiResponse}
          />
        </motion.div>
        
        {/* Map View (Mobile Only) */}
        {isMobile && activeTab === 'map' && (
          <motion.div 
            className="flex-1"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <MapView apiResponse={apiResponse} />
          </motion.div>
        )}
      </div>
    </div>
  );
} 