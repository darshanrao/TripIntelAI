import { useState, useEffect } from 'react';
import Head from 'next/head';
import ChatInterface from '../components/ChatInterface';
import ItineraryView from '../components/ItineraryView';
import MapView from '../components/MapView';
import { motion } from 'framer-motion';
import { sendChatMessage } from '../services/api';

export default function Home() {
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
    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  // Process API response when it changes
  useEffect(() => {
    if (!apiResponse) return;
    
    console.log("Processing API response in Home:", apiResponse);
    
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
            console.error('Error parsing string response:', e);
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

  const handleChatMessage = async (message, options = {}) => {
    console.log('Message from chat:', message, options);
    
    if (!message || message.trim() === '') {
      console.error('Empty message detected');
      return;
    }
    
    setIsLoading(true);
    
    try {
      // Call the API with options
      const response = await sendChatMessage(message, null, options);
      console.log('API response:', response);
      
      // Store the API response
      setApiResponse(response);
      
      if (response.error) {
        console.error('API returned an error:', response.error);
        setIsLoading(false);
        return;
      }
      
      setIsLoading(false);
    } catch (error) {
      console.error('Error processing message:', error);
      
      // Set error response
      setApiResponse({
        error: error.message,
        message: "Sorry, there was an error processing your request."
      });
      
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

  // Helper function to determine activity icon
  const getActivityIcon = (activity) => {
    const type = activity.type?.toLowerCase() || '';
    const category = activity.category?.toLowerCase() || '';
    
    if (type.includes('dining') || category.includes('lunch') || category.includes('dinner') || 
        category.includes('breakfast') || category.includes('food')) {
      return '🍽️';
    } else if (type.includes('attraction') || category.includes('museum') || category.includes('gallery') || 
               category.includes('aquarium') || category.includes('landmark')) {
      return '🏛️';
    } else if (type.includes('transportation') || category.includes('flight')) {
      return '✈️';
    } else if (type.includes('accommodation') || category.includes('hotel')) {
      return '🏨';
    } else if (category.includes('park') || category.includes('nature')) {
      return '🌳';
    } else if (category.includes('tour')) {
      return '🔍';
    } else {
      return '📍';
    }
  };

  // Get the current day's activities
  const currentDayActivities = itineraryData?.daily_itinerary[`day_${selectedDay}`]?.activities || [];

  // Handle activity hover/click to center map  
  const handleActivityHover = (id) => {
    console.log(`Parent received activity ID: ${id}`);
    setHoveredActivityId(id);
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <Head>
        <title>Travel Itinerary AI</title>
        <meta name="description" content="AI-powered travel itinerary planner" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

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
            <p className="mt-4 text-gray-700">Generating your itinerary...</p>
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
            key="chat-interface"
          />
        </motion.div>

        {/* Middle Column - Itinerary View */}
        <motion.div 
          className={`${isMobile ? (activeTab === 'itinerary' ? 'flex-1' : 'hidden') : 'w-1/3 border-r'} flex flex-col bg-white`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          {itineraryData ? (
            <ItineraryView 
              itineraryData={itineraryData}
              apiResponse={apiResponse}
              onDayChange={(day) => setSelectedDay(day)}
              onActivityHover={handleActivityHover}
              key="itinerary-view"
            />
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <p>Start chatting to generate your itinerary</p>
            </div>
          )}
        </motion.div>

        {/* Right Column - Map View */}
        <motion.div 
          className={`${isMobile ? (activeTab === 'map' ? 'flex-1' : 'hidden') : 'w-1/3'} flex flex-col`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <MapView 
            activities={currentDayActivities}
            selectedDay={selectedDay}
            itineraryData={itineraryData}
            key="map-view"
            calculateRoutes={false}
            hoveredActivityId={hoveredActivityId}
          />
        </motion.div>
      </div>
    </div>
  );
} 