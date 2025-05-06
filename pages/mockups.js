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
  const [hoveredActivityId, setHoveredActivityId] = useState(null);

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
    console.log('Message from chat in mockups page:', message);
    
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
    console.log("Processing itinerary response:", typeof response, response);
    
    if (!response) {
      console.error('Empty response received');
      return;
    }

    try {
      // Ensure response is an object, not a string
      let data = response;
      if (typeof response === 'string') {
        try {
          data = JSON.parse(response);
          console.log("Successfully parsed string response to JSON object");
        } catch (e) {
          console.error("Failed to parse response string to JSON:", e);
          // If parsing fails, try to create a minimal valid object
          data = { error: "Invalid response format" };
        }
      }

      // Transform the data into the expected format for both views
      const processedData = {
        trip_summary: data.trip_summary || null,
        daily_itinerary: data.daily_itinerary || {},
        review_highlights: data.review_highlights || null,
        flights: data.flights || []
      };
      
      // Validate the daily_itinerary structure
      if (processedData.daily_itinerary) {
        // Log all the day keys we found
        const dayKeys = Object.keys(processedData.daily_itinerary);
        console.log(`Itinerary has ${dayKeys.length} days:`, dayKeys.join(', '));
        
        // Ensure each day has a valid activities array
        dayKeys.forEach(dayKey => {
          const day = processedData.daily_itinerary[dayKey];
          if (day) {
            if (!day.activities) {
              console.warn(`Creating empty activities array for ${dayKey}`);
              day.activities = [];
            } else if (!Array.isArray(day.activities)) {
              console.warn(`Converting activities to array for ${dayKey}`);
              try {
                // If it's an object with numeric keys, convert to array
                day.activities = Object.values(day.activities);
              } catch (e) {
                console.error(`Failed to convert activities for ${dayKey}:`, e);
                day.activities = [];
              }
            }
          }
        });
      }
      
      console.log("Processed itinerary data:", processedData);
      setItineraryData(processedData);
    } catch (error) {
      console.error('Error processing itinerary data:', error);
    }
  };

  // Handle activity hover/click to center map
  const handleActivityHover = (id) => {
    console.log(`Mockups page received activity ID: ${id}`);
    setHoveredActivityId(id);
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
            onDayChange={(day) => setSelectedDay(day)}
            onActivityHover={handleActivityHover}
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
            <MapView 
              apiResponse={apiResponse}
              itineraryData={itineraryData}
              selectedDay={selectedDay}
              key="mockup-map-view-stable" 
              calculateRoutes={false}
              hoveredActivityId={hoveredActivityId}
            />
          </motion.div>
        )}
      </div>
    </div>
  );
} 