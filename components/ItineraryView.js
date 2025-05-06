import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tab } from '@headlessui/react';

const ItineraryView = ({ itineraryData, apiResponse }) => {
  const [itineraryMessages, setItineraryMessages] = useState([]);
  const [selectedDay, setSelectedDay] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [hoveredActivity, setHoveredActivity] = useState(null);
  const [dataLoaded, setDataLoaded] = useState(false);
  const timelineRef = useRef(null);
  
  // DEBUG: Log props on every render
  console.log("ItineraryView render - props received:", { 
    itineraryData: itineraryData ? "Present" : "Missing", 
    apiResponse: apiResponse ? "Present" : "Missing" 
  });

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

  // Process and cache itinerary data to avoid data loss on refresh
  const processItineraryData = (data) => {
    if (!data) return;
    
    console.log("Processing itinerary data with processItineraryData():", data);
    setIsProcessing(true);
    
    try {
      // Cache the data to localStorage for persistence
      localStorage.setItem('cachedItineraryData', JSON.stringify(data));
      
      // Process the data
      const messages = parseItineraryToMessages(data);
      
      if (messages && messages.length > 0) {
        console.log("Setting itinerary messages:", messages.length);
        setItineraryMessages(messages);
        setDataLoaded(true);
      } else {
        console.warn("No messages generated from data");
        
        // If no messages were generated, try loading mock data as a fallback
        console.log("Attempting to load mock data as fallback");
        loadMockDataAsFallback();
      }
    } catch (error) {
      console.error("Error processing itinerary data:", error);
      
      // If an error occurs, try loading mock data as a fallback
      loadMockDataAsFallback();
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Load mock data as a fallback
  const loadMockDataAsFallback = () => {
    console.log("Loading mock data as fallback");
    
    import('../services/mockData')
      .then(module => {
        console.log("Loaded mock data module:", module);
        if (module.mockItineraryData) {
          console.log("Found mockItineraryData in module");
          try {
            // Try with the original data first
            const messages = parseItineraryToMessages(module.mockItineraryData);
            
            if (messages && messages.length > 0) {
              console.log("Setting itinerary messages from mock data:", messages.length);
              setItineraryMessages(messages);
              setDataLoaded(true);
              
              // Cache this successful data
              localStorage.setItem('cachedItineraryData', JSON.stringify(module.mockItineraryData));
              return;
            }
          } catch (e) {
            console.error("Error processing mock data:", e);
          }
        }
      })
      .catch(err => {
        console.error("Failed to load mock data:", err);
      });
  };

  // On mount, attempt to load data from multiple sources
  useEffect(() => {
    // Try to load cached data first
    const cachedData = localStorage.getItem('cachedItineraryData');
    let loadedFromCache = false;
    
    if (cachedData) {
      try {
        const parsedData = JSON.parse(cachedData);
        console.log("Found cached itinerary data:", parsedData);
        processItineraryData(parsedData);
        loadedFromCache = true;
      } catch (e) {
        console.error("Error parsing cached itinerary data:", e);
      }
    }
    
    // If no cached data and no props yet, try to preload mock data
    if (!loadedFromCache && !itineraryData && !apiResponse) {
      console.log("No cached data or props. Attempting to preload mock data");
      import('../services/mockData')
        .then(module => {
          // Check if we've already received itineraryData or apiResponse in the meantime
          if (!itineraryMessages.length) {
            console.log("Preloading mock data");
            processItineraryData(module.mockItineraryData);
          }
        })
        .catch(e => console.error("Error preloading mock data:", e));
    }
    
    // Set a flag to ensure we don't show loading indefinitely
    const timeout = setTimeout(() => {
      if (!dataLoaded && isProcessing) {
        console.log("Data loading timeout reached - resetting processing state");
        setIsProcessing(false);
      }
    }, 5000); // 5 second timeout
    
    return () => clearTimeout(timeout);
  }, []);
  
  // Handle direct itineraryData prop changes
  useEffect(() => {
    if (!itineraryData) return;
    
    console.log("Processing direct itineraryData prop:", itineraryData);
    processItineraryData(itineraryData);
  }, [itineraryData]);

  // Process API response when it changes
  useEffect(() => {
    if (!apiResponse) return;
    
    console.log("Processing apiResponse in ItineraryView:", apiResponse);
    setIsProcessing(true);
    
    try {
      // Extract itinerary data from various potential locations in the response
      let extractedData = null;
      
      // Handle different possible response structures
      if (apiResponse.data) {
        console.log("Found apiResponse.data", apiResponse.data);
        if (apiResponse.data.itinerary) {
          extractedData = apiResponse.data.itinerary;
        } else if (apiResponse.data.daily_itinerary) {
          extractedData = apiResponse.data;
        } else {
          // If data exists but doesn't have expected structure, use it directly
          extractedData = apiResponse.data;
        }
      } else if (apiResponse.response) {
        console.log("Found apiResponse.response", typeof apiResponse.response);
        if (typeof apiResponse.response === 'string') {
          try {
            const parsedResponse = JSON.parse(apiResponse.response);
            console.log("Parsed response from string:", parsedResponse);
            extractedData = parsedResponse;
          } catch (e) {
            console.error('Error parsing response JSON:', e);
          }
        } else {
          extractedData = apiResponse.response;
        }
      } else if (apiResponse.itinerary) {
        extractedData = apiResponse.itinerary;
      } else if (typeof apiResponse === 'object' && apiResponse.trip_summary) {
        // Direct itinerary object
        extractedData = apiResponse;
      }
      
      if (extractedData) {
        console.log("Extracted itinerary data from apiResponse:", extractedData);
        processItineraryData(extractedData);
      } else {
        console.warn("No itinerary data found in apiResponse");
        setIsProcessing(false);
      }
    } catch (error) {
      console.error("Error processing apiResponse:", error);
      setIsProcessing(false);
    }
  }, [apiResponse]);

  // Parse itinerary data into structured messages
  const parseItineraryToMessages = (data) => {
    console.log("parseItineraryToMessages input:", typeof data, data);
    
    // Enhanced validation and better logging
    if (!data) {
      console.warn('No data provided to parseItineraryToMessages');
      return [];
    }
    
    // Log detailed structure to help with debugging
    try {
      console.log("Data structure check:", {
        hasItinerary: !!data.itinerary,
        hasTripSummary: !!(data.trip_summary || (data.itinerary && data.itinerary.trip_summary)),
        hasDailyItinerary: !!(data.daily_itinerary || (data.itinerary && data.itinerary.daily_itinerary)),
        tripSummaryKeys: data.trip_summary ? Object.keys(data.trip_summary) : 
                         (data.itinerary && data.itinerary.trip_summary ? Object.keys(data.itinerary.trip_summary) : []),
      });
    } catch (e) {
      console.error("Error inspecting data structure:", e);
    }
    
    const messages = [];

    try {
      // Check if we need to unwrap the data object and handle multiple possible structures
      let itineraryData = data;
      
      // Handle different possible data structures
      if (data.itinerary) {
        itineraryData = data.itinerary;
      } else if (data.data && data.data.itinerary) {
        itineraryData = data.data.itinerary;
      } else if (typeof data === 'string') {
        // Try to parse string data as JSON
        try {
          const parsedData = JSON.parse(data);
          if (parsedData.itinerary) {
            itineraryData = parsedData.itinerary;
          } else if (parsedData.trip_summary || parsedData.daily_itinerary) {
            itineraryData = parsedData;
          } else if (parsedData.data && parsedData.data.itinerary) {
            itineraryData = parsedData.data.itinerary;
          }
        } catch (e) {
          console.error("Failed to parse string data as JSON:", e);
        }
      } else if (data.response && typeof data.response === 'string') {
        // Try to parse response string as JSON
        try {
          const parsedResponse = JSON.parse(data.response);
          if (parsedResponse.data && parsedResponse.data.itinerary) {
            itineraryData = parsedResponse.data.itinerary;
          } else if (parsedResponse.itinerary) {
            itineraryData = parsedResponse.itinerary;
          } else if (parsedResponse.trip_summary || parsedResponse.daily_itinerary) {
            itineraryData = parsedResponse;
          }
        } catch (e) {
          console.error("Failed to parse response string as JSON:", e);
        }
      }
      
      console.log("Processing itinerary data after unwrapping:", itineraryData);
      
      // Add trip summary message if trip_summary exists
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
        console.log("✅ Added trip summary message");
      } else {
        console.warn("❌ No trip_summary found in data");
      }

      // Add daily itinerary messages if daily_itinerary exists
      if (itineraryData.daily_itinerary) {
        const dayEntries = Object.entries(itineraryData.daily_itinerary);
        console.log(`Found ${dayEntries.length} days in daily_itinerary`);
        
        dayEntries.forEach(([day, dayData]) => {
          if (!dayData || !dayData.activities) {
            console.warn(`❌ Missing or invalid data for ${day}`);
            return; // Skip if no data for this day
          }
          
          // Extract day number from string like "day_1" to get 1
          const dayNumber = parseInt(day.replace('day_', ''));
          if (isNaN(dayNumber)) {
            console.warn(`❌ Could not parse day number from ${day}`);
            return;
          }

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
              },
              // Include review insights data
              review_insights: activity.review_insights || null
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
            console.log(`✅ Added day ${dayNumber} message with ${activities.length} activities`);
          } else {
            console.warn(`❌ No valid activities found for day ${dayNumber}`);
          }
        });
      } else {
        console.warn("❌ No daily_itinerary found in data");
      }

      // Sort messages by day number
      const sortedMessages = messages.sort((a, b) => {
        if (a.type === 'summary') return -1;
        if (b.type === 'summary') return 1;
        return a.dayNumber - b.dayNumber;
      });
      
      if (sortedMessages.length === 0) {
        // If no messages were generated, try to create a default message from the data
        console.warn("No structured messages could be created from data. Attempting to create default message.");
        
        // Create a generic error message with information about what was in the data
        messages.push({
          id: Date.now(),
          type: 'error',
          content: "Could not parse itinerary data properly. The data might be in an unexpected format."
        });
        
        // Try to add a raw summary message if possible
        if (typeof data === 'object' && data !== null) {
          const keys = Object.keys(data);
          if (keys.length > 0) {
            messages.push({
              id: Date.now() + 1,
              type: 'summary',
              content: {
                destination: 'Data available but format unknown',
                startDate: 'Unknown',
                endDate: 'Unknown',
                duration: 0,
                budget: 0
              }
            });
          }
        }
      }
      
      console.log(`Generated ${sortedMessages.length} itinerary messages`);
      return sortedMessages;
    } catch (error) {
      console.error("Error in parseItineraryToMessages:", error);
      
      // Add an error message to display to the user
      return [{
        id: Date.now(),
        type: 'error',
        content: "An error occurred while processing the itinerary data. Please try refreshing the page."
      }];
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
                      className={`rounded-lg p-4 transition-all duration-300 cursor-pointer ${
                        hoveredActivity === activity.id 
                          ? "bg-white shadow-md ring-1 ring-primary/20" 
                          : "bg-gray-50 hover:bg-gray-100"
                      }`}
                      style={{ 
                        minHeight: hoveredActivity === activity.id ? '140px' : 'auto',
                        transform: hoveredActivity === activity.id ? 'scale(1.02)' : 'scale(1)'
                      }}
                      onMouseEnter={() => setHoveredActivity(activity.id)}
                      onMouseLeave={() => setHoveredActivity(null)}
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

                      {/* Review insights - shown on hover */}
                      <AnimatePresence>
                        {hoveredActivity === activity.id && activity.review_insights && (
                          <motion.div 
                            className="mt-3 pt-3 border-t border-gray-200"
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                          >
                            <div className="flex items-center mb-2">
                              <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                                activity.review_insights.sentiment === 'positive' 
                                  ? 'bg-green-100 text-green-800' 
                                  : 'bg-orange-100 text-orange-800'
                              }`}>
                                {activity.review_insights.sentiment === 'positive' ? '👍 RECOMMENDED' : '⚠️ MIXED REVIEWS'}
                              </span>
                            </div>

                            {activity.review_insights.strengths && activity.review_insights.strengths.length > 0 && (
                              <div className="mb-2">
                                <h6 className="text-xs font-semibold text-green-700 mb-1">HIGHLIGHTS</h6>
                                <ul className="space-y-1">
                                  {activity.review_insights.strengths.map((strength, i) => (
                                    <li key={i} className="text-sm flex items-start">
                                      <span className="text-green-500 mr-1">✓</span> {strength}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {activity.review_insights.weaknesses && activity.review_insights.weaknesses.length > 0 && (
                              <div className="mb-2">
                                <h6 className="text-xs font-semibold text-orange-700 mb-1">CONSIDERATIONS</h6>
                                <ul className="space-y-1">
                                  {activity.review_insights.weaknesses.map((weakness, i) => (
                                    <li key={i} className="text-sm flex items-start">
                                      <span className="text-orange-500 mr-1">!</span> {weakness}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {activity.review_insights.summary && (
                              <p className="text-sm text-gray-600 mt-2 italic">
                                "{activity.review_insights.summary}"
                              </p>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
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
        <div className="flex flex-col items-center text-gray-500">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-3"></div>
          <div>Processing itinerary...</div>
        </div>
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
          <button 
            className="mt-4 text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-md text-gray-700 transition-colors"
            onClick={() => {
              // Attempt to load mock data directly
              import('../services/mockData').then(module => {
                console.log("Loaded mock data module:", module);
                processItineraryData(module.mockItineraryData);
              }).catch(err => {
                console.error("Failed to load mock data:", err);
              });
            }}
          >
            Load Sample Itinerary
          </button>
          <p className="text-xs mt-4 text-gray-400">If you've already created an itinerary, try refreshing the page</p>
        </div>
      </div>
    );
  }

  // Get days for tabs
  const days = itineraryMessages.filter(msg => msg.type === 'day');

  return (
    <div className="flex flex-col h-full bg-gray-50 max-h-full overflow-hidden">
      {/* Always show summary at the top if available */}
      {itineraryMessages.find(msg => msg.type === 'summary') && (
        <div className="p-4 overflow-y-auto">
          {renderItineraryMessage(itineraryMessages.find(msg => msg.type === 'summary'))}
        </div>
      )}
      
      {days.length > 0 ? (
        <Tab.Group as="div" className="flex flex-col flex-grow overflow-hidden">
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

          <Tab.Panels className="flex-grow overflow-y-auto">
            {days.map((day) => (
              <Tab.Panel key={day.id} className="h-full overflow-y-auto p-4">
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