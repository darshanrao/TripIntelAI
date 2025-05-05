import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tab } from '@headlessui/react';

const ItineraryView = ({ itineraryData, apiResponse }) => {
  const [itineraryMessages, setItineraryMessages] = useState([]);
  const [selectedDay, setSelectedDay] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const timelineRef = useRef(null);

  // Helper function to format itinerary text from response data - Similar to ChatInterface
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
    
    return text;
  };

  // CRITICAL FIX: Direct processing of itineraryData when it's passed as a prop
  useEffect(() => {
    if (!itineraryData) return;
    
    console.log("Processing direct itineraryData prop:", itineraryData);
    setIsProcessing(true);
    
    try {
      // Directly process the data from the prop into messages
      const messages = parseItineraryToMessages(itineraryData);
      
      if (messages && messages.length > 0) {
        console.log("Setting itinerary messages from prop data:", messages.length);
        setItineraryMessages(messages);
      } else {
        console.warn("No messages generated from itineraryData prop");
      }
    } catch (error) {
      console.error("Error processing itineraryData prop:", error);
    } finally {
      setIsProcessing(false);
    }
  }, [itineraryData]);
  
  // Process API response when it changes
  useEffect(() => {
    if (!apiResponse) return;
    
    console.log("Processing apiResponse in ItineraryView:", apiResponse);
    setIsProcessing(true);
    
    try {
      // Extract itinerary data from various potential locations in the response
      let extractedData = null;
      
      if (apiResponse.data?.itinerary) {
        extractedData = apiResponse.data.itinerary;
      } else if (apiResponse.data?.daily_itinerary) {
        extractedData = apiResponse.data;
      } else if (apiResponse.response) {
        if (typeof apiResponse.response === 'string') {
          try {
            const parsedResponse = JSON.parse(apiResponse.response);
            extractedData = parsedResponse;
          } catch (e) {
            console.error('Error parsing response JSON:', e);
          }
        } else {
          extractedData = apiResponse.response;
        }
      } else if (apiResponse.itinerary) {
        extractedData = apiResponse.itinerary;
      }
      
      if (extractedData) {
        console.log("Extracted itinerary data from apiResponse");
        const messages = parseItineraryToMessages(extractedData);
        
        if (messages && messages.length > 0) {
          console.log("Setting itinerary messages from apiResponse:", messages.length);
          setItineraryMessages(messages);
        } else {
          console.warn("No messages generated from apiResponse data");
        }
      } else {
        console.warn("No itinerary data found in apiResponse");
      }
    } catch (error) {
      console.error("Error processing apiResponse:", error);
    } finally {
      setIsProcessing(false);
    }
  }, [apiResponse]);

  // Parse itinerary data into structured messages
  const parseItineraryToMessages = (data) => {
    console.log("parseItineraryToMessages input:", typeof data, data);
    const messages = [];

    try {
      // Check if we need to unwrap the data object
      let itineraryData = data;
      if (data.itinerary) {
        itineraryData = data.itinerary;
      } else if (data.data && data.data.itinerary) {
        itineraryData = data.data.itinerary;
      }
      
      console.log("Processing itinerary data:", itineraryData);
      
      // Add trip summary message
      if (itineraryData.trip_summary) {
        messages.push({
          id: Date.now(),
          type: 'summary',
          content: {
            destination: itineraryData.trip_summary.destination || 'Not specified',
            startDate: itineraryData.trip_summary.start_date || 'Not specified',
            endDate: itineraryData.trip_summary.end_date || 'Not specified',
            duration: itineraryData.trip_summary.duration_days || 0,
            budget: itineraryData.trip_summary.total_budget || 0
          }
        });
      }

      // Add daily itinerary messages
      if (itineraryData.daily_itinerary) {
        Object.entries(itineraryData.daily_itinerary).forEach(([day, dayData]) => {
          if (!dayData || !dayData.activities) return;
          
          // Extract day number from string like "day_1" to get 1
          const dayNumber = parseInt(day.replace('day_', ''));
          if (isNaN(dayNumber)) return;

          console.log(`Processing day ${dayNumber} with ${dayData.activities.length} activities`);
          
          const activities = Array.isArray(dayData.activities) ? dayData.activities.map(activity => {
            if (!activity) return null;
            
            return {
              id: Math.random().toString(36).substr(2, 9),
              time: activity.time || '',
              title: activity.title || '',
              category: activity.category || 'Other',
              icon: getActivityIcon(activity),
              details: {
                location: activity.details?.location || '',
                description: activity.details?.description || '',
                duration: activity.duration_minutes || 0,
                cost: activity.cost || 0
              }
            };
          }).filter(Boolean) : [];

          if (activities.length > 0) {
            messages.push({
              id: Date.now() + dayNumber,
              type: 'day',
              dayNumber: dayNumber,
              date: dayData.date || '',
              activities: groupActivitiesByCategory(activities)
            });
          }
        });
      }

      // Sort messages by day number
      const sortedMessages = messages.sort((a, b) => {
        if (a.type === 'summary') return -1;
        if (b.type === 'summary') return 1;
        return a.dayNumber - b.dayNumber;
      });
      
      console.log(`Generated ${sortedMessages.length} itinerary messages`);
      return sortedMessages;
    } catch (error) {
      console.error("Error in parseItineraryToMessages:", error);
      return [];
    }
  };

  // Helper function to get activity icon
  const getActivityIcon = (activity) => {
    const type = activity.type?.toLowerCase() || '';
    const category = activity.category?.toLowerCase() || '';
    
    if (type.includes('dining') || category.includes('food') || category.includes('lunch') || 
        category.includes('dinner') || category.includes('breakfast')) return '🍽️';
    if (type.includes('attraction') || category.includes('museum') || category.includes('gallery') || 
        category.includes('landmark')) return '🏛️';
    if (type.includes('transportation')) return '✈️';
    if (type.includes('accommodation') || category.includes('hotel')) return '🏨';
    if (category.includes('nature') || category.includes('park')) return '🌳';
    if (category.includes('tour')) return '🔍';
    return '📍';
  };

  // Group activities by category
  const groupActivitiesByCategory = (activities) => {
    return activities.reduce((acc, activity) => {
      const category = activity.category;
      if (!acc[category]) acc[category] = [];
      acc[category].push(activity);
      return acc;
    }, {});
  };

  // Render a single itinerary message
  const renderItineraryMessage = (message) => {
    switch (message.type) {
      case 'summary':
        return (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-lg shadow-sm p-6 mb-4"
          >
            <h2 className="text-2xl font-bold mb-4">Trip Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <div>
                  <label className="text-gray-600 text-sm">Destination</label>
                  <p className="text-lg font-medium">{message.content.destination}</p>
                </div>
                <div>
                  <label className="text-gray-600 text-sm">Duration</label>
                  <p className="text-lg font-medium">{message.content.duration} days</p>
                </div>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="text-gray-600 text-sm">Dates</label>
                  <p className="text-lg font-medium">{message.content.startDate} - {message.content.endDate}</p>
                </div>
                <div>
                  <label className="text-gray-600 text-sm">Total Budget</label>
                  <p className="text-lg font-medium">${typeof message.content.budget === 'number' ? message.content.budget.toFixed(2) : '0.00'}</p>
                </div>
              </div>
            </div>
          </motion.div>
        );

      case 'day':
        return (
          <motion.div
            key={message.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white rounded-lg shadow-sm p-6 mb-4"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold">Day {message.dayNumber}</h3>
              {message.date && (
                <span className="text-gray-500">{message.date}</span>
              )}
            </div>
            {Object.entries(message.activities).map(([category, activities]) => (
              <div key={category} className="mb-6">
                <h4 className="text-lg font-semibold mb-3 text-gray-700">{category}</h4>
                <div className="space-y-4">
                  {activities.map((activity) => (
                    <motion.div
                      key={activity.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-gray-50 rounded-lg p-4"
                    >
                      <div className="flex items-center mb-2">
                        <span className="text-2xl mr-3">{activity.icon}</span>
                        <div>
                          <h5 className="font-medium">{activity.title}</h5>
                          <p className="text-sm text-gray-600">{activity.time}</p>
                        </div>
                      </div>
                      {activity.details.location && (
                        <div className="ml-9 text-sm text-gray-600">
                          <p>📍 {activity.details.location}</p>
                          {activity.details.description && (
                            <p className="mt-1">{activity.details.description}</p>
                          )}
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </div>
            ))}
          </motion.div>
        );

      case 'error':
        return (
          <motion.div
            key={message.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-red-50 text-red-600 rounded-lg p-4 mb-4"
          >
            {message.content}
          </motion.div>
        );

      default:
        return null;
    }
  };

  // Loading state
  if (isProcessing) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Processing itinerary...</div>
      </div>
    );
  }

  // Empty state
  if (!itineraryMessages.length) {
    return (
      <div className="flex items-center justify-center h-full p-4">
        <div className="text-center text-gray-500 p-8 border border-gray-200 rounded-lg shadow-sm bg-white">
          <p className="mb-2 font-semibold">No itinerary data available</p>
          <p className="text-sm">Start chatting with the AI to generate an itinerary</p>
          <p className="text-xs mt-4 text-gray-400">If you've already created an itinerary, try refreshing the page</p>
        </div>
      </div>
    );
  }

  // Get days for tabs
  const days = itineraryMessages.filter(msg => msg.type === 'day');

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Always show summary at the top if available */}
      {itineraryMessages.find(msg => msg.type === 'summary') && (
        <div className="p-4">
          {renderItineraryMessage(itineraryMessages.find(msg => msg.type === 'summary'))}
        </div>
      )}
      
      {days.length > 0 ? (
        <Tab.Group>
          <Tab.List className="flex space-x-2 p-4 bg-white shadow-sm overflow-x-auto">
            {days.map((day) => (
              <Tab
                key={day.id}
                className={({ selected }) =>
                  `px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap
                  ${selected 
                    ? 'bg-primary text-white shadow-md' 
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}`
                }
              >
                Day {day.dayNumber}
                {day.date && <span className="ml-2 opacity-75">({day.date})</span>}
              </Tab>
            ))}
          </Tab.List>

          <Tab.Panels className="flex-1 overflow-y-auto p-4">
            {days.map((day) => (
              <Tab.Panel key={day.id}>
                {renderItineraryMessage(day)}
              </Tab.Panel>
            ))}
          </Tab.Panels>
        </Tab.Group>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-gray-500">No daily itinerary available yet</p>
        </div>
      )}
    </div>
  );
};

export default ItineraryView; 