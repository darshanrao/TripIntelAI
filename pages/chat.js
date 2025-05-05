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

  const handleChatMessage = async (message) => {
    console.log('Message from chat:', message);
    
    if (!message || message.trim() === '') {
      console.error('Empty message detected');
      return;
    }
    
    setIsLoading(true);
    
    try {
      // Call the actual API with proper parameters
      const response = await sendChatMessage(message);
      console.log('API response:', response);
      
      // Store the API response to pass to the ChatInterface
      setApiResponse(response);
      
      if (response.error) {
        console.error('API returned an error:', response.error);
        setIsLoading(false);
        return;
      }
      
      // Process itinerary data for the middle and right columns
      if (response.data?.daily_itinerary) {
        processItineraryResponse(response.data);
      } else if (response.response) {
        if (typeof response.response === 'string') {
          try {
            const parsedResponse = JSON.parse(response.response);
            processItineraryResponse(parsedResponse);
          } catch (e) {
            console.error('Error parsing string response:', e);
          }
        } else {
          processItineraryResponse(response.response);
        }
      } else if (response.itinerary && typeof response.itinerary === 'object') {
        processItineraryResponse(response.itinerary);
      }
      
      // If on mobile, switch to itinerary view when we have data
      if (isMobile && itineraryData) {
        setActiveTab('itinerary');
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
    if (response.daily_itinerary) {
      // Transform the itinerary data for display
      const days = Object.keys(response.daily_itinerary).map(dayNum => {
        const dayData = response.daily_itinerary[dayNum];
        const activities = Array.isArray(dayData.activities) 
          ? dayData.activities.map(activity => ({
              time: activity.time || '',
              title: activity.title || '',
              description: activity.details?.location || '',
              icon: getActivityIcon(activity),
              location: activity.details?.location ? {
                lat: 0, // You'll need to geocode these addresses
                lng: 0
              } : null
            }))
          : [];
        
        return {
          day: parseInt(dayNum.replace('day_', '')),
          activities
        };
      });
      
      setItineraryData({ days });
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
  const currentDayActivities = itineraryData?.days.find(day => day.day === selectedDay)?.activities || [];

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
          className={`${isMobile ? (activeTab === 'itinerary' ? 'flex-1' : 'hidden') : 'w-1/3 border-r'} flex flex-col`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <ItineraryView 
            days={itineraryData?.days || []} 
            selectedDay={selectedDay} 
            onSelectDay={setSelectedDay}
          />
        </motion.div>

        {/* Right Column - Map View */}
        <motion.div 
          className={`${isMobile ? (activeTab === 'map' ? 'flex-1' : 'hidden') : 'w-1/3'} flex flex-col`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <MapView 
            activities={currentDayActivities} 
            day={selectedDay}
          />
        </motion.div>
      </div>
    </div>
  );
} 