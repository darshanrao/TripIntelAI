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

  // Default sample itinerary for development/demo
  const sampleItinerary = {
    days: [
      {
        day: 1,
        activities: [
          { time: '09:00 AM', title: 'Empire State Building', description: 'Visit the iconic skyscraper', icon: '🏙️', location: { lat: 40.7484, lng: -73.9857 } },
          { time: '12:30 PM', title: 'Lunch at Chelsea Market', description: 'Explore diverse food options', icon: '🍽️', location: { lat: 40.7420, lng: -74.0048 } },
          { time: '02:30 PM', title: 'High Line Walk', description: 'Stroll along the elevated park', icon: '🚶', location: { lat: 40.7480, lng: -74.0048 } },
          { time: '05:00 PM', title: 'Museum of Modern Art', description: 'Explore contemporary art', icon: '🏛️', location: { lat: 40.7614, lng: -73.9776 } },
          { time: '08:00 PM', title: 'Dinner at Little Italy', description: 'Authentic Italian cuisine', icon: '🍝', location: { lat: 40.7197, lng: -73.9970 } },
        ]
      },
      {
        day: 2,
        activities: [
          { time: '10:00 AM', title: 'Central Park Bike Tour', description: 'Cycle through the scenic park', icon: '🚲', location: { lat: 40.7812, lng: -73.9665 } },
          { time: '01:00 PM', title: 'Metropolitan Museum', description: 'World-class art collection', icon: '🖼️', location: { lat: 40.7794, lng: -73.9632 } },
          { time: '04:00 PM', title: 'Times Square', description: 'Experience the bright lights', icon: '✨', location: { lat: 40.7580, lng: -73.9855 } },
          { time: '07:30 PM', title: 'Broadway Show', description: 'Evening entertainment', icon: '🎭', location: { lat: 40.7590, lng: -73.9845 } },
        ]
      }
    ]
  };

  useEffect(() => {
    // Check if the screen is mobile
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    // Set initial itinerary data
    setItineraryData(sampleItinerary);
    
    // Add window resize listener
    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  // Function to parse itinerary text from AI response
  const parseItineraryFromText = (text) => {
    try {
      // Check if the text contains JSON
      if (text.includes('{') && text.includes('}')) {
        // Try to extract JSON from text
        const jsonMatch = text.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const jsonData = JSON.parse(jsonMatch[0]);
          return jsonData;
        }
      }
      
      // If no JSON found, try to parse the text format
      // This is a simple example - in a real app, use more sophisticated parsing
      const days = [];
      const dayMatches = text.match(/Day \d+:[\s\S]*?(?=Day \d+:|$)/g);
      
      if (dayMatches) {
        dayMatches.forEach((dayText, index) => {
          const dayNumber = index + 1;
          const activities = [];
          
          // Extract activities with time, title, and description
          const activityMatches = dayText.match(/(\d{1,2}:\d{2} [AP]M)[\s-]*([^:]+)(?:: (.+))?/g);
          
          if (activityMatches) {
            activityMatches.forEach((activityText, actIndex) => {
              const timeMatch = activityText.match(/(\d{1,2}:\d{2} [AP]M)/);
              const time = timeMatch ? timeMatch[1] : '';
              
              // Remove time from text
              let remainingText = activityText.replace(time, '').trim();
              remainingText = remainingText.replace(/^[-:]\s*/, '');
              
              // Split into title and description if possible
              let title = remainingText;
              let description = '';
              
              if (remainingText.includes(':')) {
                const parts = remainingText.split(':');
                title = parts[0].trim();
                description = parts[1].trim();
              }
              
              // Assign an appropriate icon based on keywords
              let icon = '📍';
              if (/breakfast|lunch|dinner|cafe|restaurant|food|eat/i.test(title)) {
                icon = '🍽️';
              } else if (/museum|gallery|art|exhibit/i.test(title)) {
                icon = '🏛️';
              } else if (/park|garden|nature|walk|hike/i.test(title)) {
                icon = '🌳';
              } else if (/hotel|accommodation|stay|check|inn/i.test(title)) {
                icon = '🏨';
              } else if (/tour|visit|explore/i.test(title)) {
                icon = '🔍';
              } else if (/show|theater|concert|music|performance/i.test(title)) {
                icon = '🎭';
              } else if (/beach|ocean|sea|swim/i.test(title)) {
                icon = '🏖️';
              }
              
              // Create mock location (in a real app, use geocoding API)
              // For demo purposes, creating locations around central NYC with slight variations
              const location = {
                lat: 40.7580 + (Math.random() * 0.1 - 0.05),
                lng: -73.9855 + (Math.random() * 0.1 - 0.05)
              };
              
              activities.push({ time, title, description, icon, location });
            });
          }
          
          days.push({ day: dayNumber, activities });
        });
      }
      
      return { days };
    } catch (error) {
      console.error('Error parsing itinerary:', error);
      return null;
    }
  };

  // Handle message from chat
  const handleChatMessage = async (message) => {
    console.log('Message from chat:', message);
    
    // If there's already an itinerary, process messages directly
    if (itineraryData && itineraryData.days && itineraryData.days.length > 0) {
      // In a real app, we would use this to refine/modify the existing itinerary
      return;
    }
    
    setIsLoading(true);
    
    try {
      // In a real implementation, this would be integrated with your backend
      // This is just simulating API behavior for demonstration
      
      // Detect if message looks like a trip request
      const isTripRequest = /(?:plan|create|make|generate)\s+(?:a|an)?\s*(?:trip|itinerary|vacation|holiday|journey)/i.test(message) ||
                           /(?:going|travel|visit|traveling)\s+to/i.test(message);
      
      if (isTripRequest) {
        // Set a timeout to simulate API processing
        setTimeout(() => {
          // Parse the itinerary from API response
          const parsedItinerary = parseItineraryFromText(sampleItinerary);
          if (parsedItinerary) {
            setItineraryData(parsedItinerary);
            
            // If on mobile, switch to itinerary view
            if (isMobile) {
              setActiveTab('itinerary');
            }
          }
          
          setIsLoading(false);
        }, 2000);
      } else {
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Error processing message:', error);
      setIsLoading(false);
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
          <ChatInterface onSendMessage={handleChatMessage} />
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