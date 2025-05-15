import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tab } from '@headlessui/react';

const ItineraryView = ({ itineraryData, apiResponse, onDayChange, onActivityHover }) => {
  const [itineraryMessages, setItineraryMessages] = useState([]);
  const [selectedDay, setSelectedDay] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [hoveredActivity, setHoveredActivity] = useState(null);
  const [selectedActivity, setSelectedActivity] = useState(null);
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
      
      // Debug the data structure to show days
      if (data.daily_itinerary) {
        const dayKeys = Object.keys(data.daily_itinerary).sort();
        console.log("DAILY ITINERARY KEYS:", dayKeys);
        console.log("DAYS IN DATA:", dayKeys.map(key => {
          // Extract day number from the key
          const match = key.match(/day[_\s]*(\d+)/i);
          return match ? parseInt(match[1], 10) : null;
        }).filter(Boolean));
      }
      
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
    console.log("Loading direct mock data as fallback");
    
    // Use the exact mock-backend data directly instead of importing it
    const mockBackendData = {
      "trip_summary":{
         "destination":"Los Angeles",
         "start_date":"2025-06-10",
         "end_date":"2025-06-13",
         "duration_days":4,
         "total_budget":4729.13
      },
      "daily_itinerary":{
         "day_1":{
            "date":"2025-06-10",
            "activities":[
               {
                  "type":"accommodation",
                  "category":"hotel",
                  "title":"Check-in at The Ritz-Carlton, Los Angeles",
                  "time":"15:00",
                  "duration_minutes":60,
                  "details":{
                     "location":"900 West Olympic Boulevard, Los Angeles",
                     "latitude":34.0452145,
                     "longitude":-118.2666588
                  },
                  "review_insights":{
                     "sentiment":"positive",
                     "strengths":[
                        "Luxurious and elegant accommodations",
                        "Exceptional service and attentive staff"
                     ],
                     "weaknesses":[
                        "Expensive room rates and additional fees"
                     ],
                     "summary":"The Ritz-Carlton, Los Angeles offers a luxurious five-star experience with exceptional service, though guests should be prepared for premium pricing."
                  }
               },
               {
                  "type":"dining",
                  "category":"dinner",
                  "title":"Dinner at Eastside Italian Deli",
                  "time":"19:00",
                  "duration_minutes":90,
                  "details":{
                     "location":"1013 Alpine Street, Los Angeles",
                     "latitude":34.0651255,
                     "longitude":-118.2466235
                  },
                  "review_insights":{
                     "sentiment":"positive",
                     "strengths":[
                        "Authentic Italian sandwiches and food",
                        "High-quality ingredients and meats"
                     ],
                     "weaknesses":[
                        "Long lines, especially during lunch hours"
                     ],
                     "summary":"Eastside Italian Deli is a beloved, family-owned Italian deli known for authentic, high-quality sandwiches and imported Italian goods, despite long lines."
                  }
               }
            ]
         },
         "day_2":{
            "date":"2025-06-11",
            "activities":[
               {
                  "type":"attraction",
                  "category":"theme park",
                  "title":"Visit Universal Studios Hollywood",
                  "time":"09:00",
                  "duration_minutes":480,
                  "details":{
                     "location":"100 Universal City Plaza, Universal City",
                     "latitude":34.1419225,
                     "longitude":-118.358411
                  },
                  "review_insights":{
                     "sentiment":"positive",
                     "strengths":[
                        "Harry Potter Wizarding World attracts many visitors",
                        "Super Nintendo World is highly praised for its immersive experience"
                     ],
                     "weaknesses":[
                        "High ticket prices and expensive food/merchandise",
                        "Crowds and long wait times, especially on weekends and holidays"
                     ],
                     "summary":"Universal Studios Hollywood offers immersive themed areas like Wizarding World of Harry Potter and Super Nintendo World, alongside high prices and crowds during peak periods."
                  }
               },
               {
                  "type":"dining",
                  "category":"dinner",
                  "title":"Dinner at Sushi Gen",
                  "time":"19:00",
                  "duration_minutes":90,
                  "details":{
                     "location":"422 East 2nd Street, Los Angeles",
                     "latitude":34.0467296,
                     "longitude":-118.2387113
                  },
                  "review_insights":{
                     "sentiment":"positive",
                     "strengths":[
                        "Fresh, high-quality fish",
                        "Excellent sashimi deluxe lunch special"
                     ],
                     "weaknesses":[
                        "Long wait times, especially during peak hours",
                        "Limited seating and crowded dining area"
                     ],
                     "summary":"Sushi Gen is renowned for its exceptionally fresh fish and famous sashimi deluxe lunch special at reasonable prices, despite consistently long wait times."
                  }
               }
            ]
         },
         "day_3":{
            "date":"2025-06-12",
            "activities":[
               {
                  "type":"attraction",
                  "category":"park",
                  "title":"Visit Griffith Park",
                  "time":"09:00",
                  "duration_minutes":240,
                  "details":{
                     "location":"Los Angeles",
                     "latitude":34.0536909,
                     "longitude":-118.242766
                  },
                  "review_insights":{
                     "sentiment":"positive",
                     "strengths":[
                        "Breathtaking views of Los Angeles and the Hollywood Sign",
                        "Extensive hiking trails for all skill levels"
                     ],
                     "weaknesses":[
                        "Limited parking, especially on weekends and holidays",
                        "Heavy crowds during peak times"
                     ],
                     "summary":"Griffith Park offers stunning city views, extensive hiking trails, and attractions like the Griffith Observatory, though visitors should arrive early to avoid parking challenges and crowds."
                  }
               },
               {
                  "type":"dining",
                  "category":"lunch",
                  "title":"Lunch at Philippe The Original",
                  "time":"12:30",
                  "duration_minutes":90,
                  "details":{
                     "location":"1001 North Alameda Street, Los Angeles",
                     "latitude":34.0596738,
                     "longitude":-118.236941
                  },
                  "review_insights":{
                     "sentiment":"positive",
                     "strengths":[
                        "Famous French dip sandwiches",
                        "Historic establishment (opened in 1908)"
                     ],
                     "weaknesses":[
                        "Long lines during peak hours",
                        "Limited seating during busy times"
                     ],
                     "summary":"Philippe The Original is a historic Los Angeles landmark famous for inventing the French dip sandwich in 1908, despite occasional long lines."
                  }
               },
               {
                  "type":"attraction",
                  "category":"stadium",
                  "title":"Visit Dodger Stadium",
                  "time":"18:00",
                  "duration_minutes":240,
                  "details":{
                     "location":"1000 Vin Scully Ave, Los Angeles",
                     "latitude":34.0736255,
                     "longitude":-118.2398452
                  },
                  "review_insights":{
                     "sentiment":"positive",
                     "strengths":[
                        "Historic ballpark with iconic views of Los Angeles",
                        "Great baseball atmosphere and experience"
                     ],
                     "weaknesses":[
                        "Expensive parking ($30-35)",
                        "Traffic congestion before and after games"
                     ],
                     "summary":"Dodger Stadium offers an iconic baseball experience with beautiful views, though visitors should plan for expensive parking and traffic congestion."
                  }
               }
            ]
         },
         "day_4":{
            "date":"2025-06-13",
            "activities":[
               {
                  "type":"attraction",
                  "category":"museum",
                  "title":"Visit The Getty",
                  "time":"09:00",
                  "duration_minutes":240,
                  "details":{
                     "location":"1200 Getty Center Drive, Los Angeles",
                     "latitude":34.0769513,
                     "longitude":-118.475712
                  },
                  "review_insights":{
                     "sentiment":"positive",
                     "strengths":[
                        "Stunning architecture and views",
                        "Impressive art collection"
                     ],
                     "weaknesses":[
                        "Expensive parking ($20-25)",
                        "Crowded during peak times and weekends"
                     ],
                     "summary":"The Getty offers a world-class cultural experience with stunning architecture and art, though visitors should plan for parking costs and potential crowds."
                  }
               },
               {
                  "type":"dining",
                  "category":"lunch",
                  "title":"Lunch at Bottega Louie",
                  "time":"13:00",
                  "duration_minutes":90,
                  "details":{
                     "location":"700 South Grand Avenue, Los Angeles",
                     "latitude":34.047143,
                     "longitude":-118.256605
                  },
                  "review_insights":{
                     "sentiment":"positive",
                     "strengths":[
                        "High-quality pastries and macarons",
                        "Beautiful interior and ambiance"
                     ],
                     "weaknesses":[
                        "Long wait times, especially on weekends",
                        "Expensive prices"
                     ],
                     "summary":"Bottega Louie is known for its beautiful interior, photogenic desserts, and European-inspired menu, though it can be crowded with long waits and high prices."
                  }
               },
               {
                  "type":"transportation",
                  "category":"flight",
                  "title":"Depart Los Angeles on UA505",
                  "time":"18:00",
                  "duration_minutes":101,
                  "details":{
                     "airline":"UA",
                     "flight_number":"UA505",
                     "departure_time":"2025-06-13T06:00:00",
                     "arrival_time":"2025-06-13T07:41:00"
                  }
               },
               {
                  "type":"accommodation",
                  "category":"hotel",
                  "title":"Check-out from The Ritz-Carlton, Los Angeles",
                  "time":"12:00",
                  "duration_minutes":30,
                  "details":{
                     "location":"900 West Olympic Boulevard, Los Angeles",
                     "latitude":34.0452145,
                     "longitude":-118.2666588
                  }
               }
            ]
         }
      }
    };

    console.log("Using directly embedded mock data with all days:", Object.keys(mockBackendData.daily_itinerary).join(", "));
    
    // Always use the full mock data directly
    processItineraryData(mockBackendData);
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
    
    // If no cached data and no props yet, directly use the hardcoded data
    if (!loadedFromCache && !itineraryData && !apiResponse) {
      console.log("No cached data or props. Using hardcoded mock data directly");
      loadMockDataAsFallback();
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
      return createDefaultMessages();
    }
    
    // Ensure data is properly parsed as JSON if it's a string
    let parsedData = data;
    if (typeof data === 'string') {
      try {
        parsedData = JSON.parse(data);
        console.log("Successfully parsed string data to JSON:", parsedData);
      } catch (e) {
        console.error("Failed to parse string data as JSON:", e);
        return createDefaultMessages();
      }
    }
    
    const messages = [];

    try {
      // Check if we need to unwrap the data object and handle multiple possible structures
      let itineraryData = parsedData;
      
      // Handle different possible data structures
      if (parsedData.itinerary) {
        itineraryData = parsedData.itinerary;
      } else if (parsedData.data && parsedData.data.itinerary) {
        itineraryData = parsedData.data.itinerary;
      } else if (parsedData.response && typeof parsedData.response === 'string') {
        // Try to parse response string as JSON
        try {
          const parsedResponse = JSON.parse(parsedData.response);
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
      
      // STEP 1: Ensure we have a proper data structure with trip_summary and daily_itinerary
      // If itineraryData is still missing the required structure, apply defaults
      if (!itineraryData.trip_summary || !itineraryData.daily_itinerary) {
        console.log("Required structure missing or incomplete, applying default structure");
        
        // Determine days from data if possible
        const tripDuration = itineraryData.trip_summary?.duration_days || 
                            (itineraryData.daily_itinerary ? Object.keys(itineraryData.daily_itinerary).length : 0);
        const numDays = tripDuration > 0 ? tripDuration : 1; // Minimum 1 day
        
        console.log(`Creating default structure with ${numDays} days`);
        
        // Create default daily_itinerary with the appropriate number of days
        const defaultDailyItinerary = {};
        for (let i = 1; i <= numDays; i++) {
          defaultDailyItinerary[`day_${i}`] = {
            date: itineraryData.trip_summary?.start_date 
                  ? new Date(new Date(itineraryData.trip_summary.start_date).getTime() + (i-1) * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
                  : "",
            activities: [
              {
                type: i === 1 ? "accommodation" : i === numDays ? "transportation" : "attraction",
                category: i === 1 ? "hotel" : i === numDays ? "flight" : "sightseeing",
                title: i === 1 ? "Check-in at Hotel" : 
                       i === numDays ? "Departure" : 
                       `Day ${i} Activity`,
                time: i === 1 ? "15:00" : "10:00",
                duration_minutes: 60,
                details: {
                  location: "Location details would appear here"
                }
              }
            ]
          };
        }
        
        // Apply defaults while preserving any existing data
        itineraryData = {
          trip_summary: itineraryData.trip_summary || {
            destination: "Your Destination",
            start_date: new Date().toISOString().split('T')[0],
            end_date: new Date(new Date().getTime() + (numDays - 1) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            duration_days: numDays,
            total_budget: 1000.00
          },
          daily_itinerary: itineraryData.daily_itinerary || defaultDailyItinerary
        };
      }
      
      // STEP 2: Add trip summary message if trip_summary exists
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

      // STEP 3: Process daily_itinerary
      if (itineraryData.daily_itinerary) {
        console.log("EXAMINING DAILY ITINERARY STRUCTURE:", itineraryData.daily_itinerary);
        
        // Check if daily_itinerary is an array (some APIs return arrays instead of objects)
        let dayEntries = [];
        if (Array.isArray(itineraryData.daily_itinerary)) {
          console.log("daily_itinerary is an array with", itineraryData.daily_itinerary.length, "items");
          // Convert array to objects with day keys
          itineraryData.daily_itinerary.forEach((dayData, index) => {
            const dayNumber = index + 1;
            dayEntries.push({
              key: `day_${dayNumber}`,
              value: dayData,
              dayNumber: dayNumber
            });
          });
        } else {
          // It's an object with day keys
          const dayKeys = Object.keys(itineraryData.daily_itinerary);
          console.log("RAW DAY KEYS:", dayKeys.join(', '));
          
          // Extract day information from each key
          dayEntries = dayKeys.map(key => {
            let dayNumber;
            
            // Try various methods to extract day number
            const dayMatch = key.match(/day[_\s]*(\d+)/i);
            if (dayMatch && dayMatch[1]) {
              dayNumber = parseInt(dayMatch[1], 10);
            } else {
              const numMatch = key.match(/\d+/);
              if (numMatch) {
                dayNumber = parseInt(numMatch[0], 10);
              } else {
                // Fallback: use alphabetical order to assign day numbers
                dayNumber = dayKeys.indexOf(key) + 1;
              }
            }
            
            return { 
              key: key, 
              value: itineraryData.daily_itinerary[key],
              dayNumber: dayNumber
            };
          });
        }
        
        // Sort by day number so they appear in order
        dayEntries.sort((a, b) => a.dayNumber - b.dayNumber);
        
        console.log("PROCESSED DAY ENTRIES:", 
          dayEntries.map(entry => `${entry.key} (Day ${entry.dayNumber})`).join(', '));
        
        // STEP 4: Ensure we have the correct number of days
        const expectedDays = itineraryData.trip_summary?.duration_days || dayEntries.length;
        if (dayEntries.length < expectedDays) {
          console.warn(`Missing days: Expected ${expectedDays} but found ${dayEntries.length}`);
          
          // Add missing days
          for (let i = 1; i <= expectedDays; i++) {
            if (!dayEntries.some(entry => entry.dayNumber === i)) {
              console.log(`Adding missing day ${i}`);
              
              let dayDate = '';
              try {
                if (itineraryData.trip_summary?.start_date) {
                  const startDate = new Date(itineraryData.trip_summary.start_date);
                  const tempDate = new Date(startDate);
                  tempDate.setDate(startDate.getDate() + (i - 1));
                  dayDate = tempDate.toISOString().split('T')[0];
                }
              } catch (e) {
                console.error("Error calculating date:", e);
              }
              
              dayEntries.push({
                key: `day_${i}`,
                value: { 
                  date: dayDate,
                  activities: []
                },
                dayNumber: i
              });
            }
          }
          
          // Re-sort after adding missing days
          dayEntries.sort((a, b) => a.dayNumber - b.dayNumber);
        }
        
        // STEP 5: Process each day entry to create messages
        dayEntries.forEach(({ key, value, dayNumber }) => {
          // For debugging
          console.log(`Processing day ${dayNumber} (${key})`, value);
          
          // Ensure activities is an array
          let activities = [];
          if (value && value.activities) {
            if (Array.isArray(value.activities)) {
              activities = value.activities;
            } else if (typeof value.activities === 'object') {
              // Try to convert from object to array
              activities = Object.values(value.activities);
            }
          }
          
          console.log(`Day ${dayNumber} has ${activities.length} activities`);
          
          // Process activities into our standard format
          const processedActivities = activities.map(activity => {
            if (!activity) return null;
            
            // Ensure activity has a consistent ID
            const activityId = activity.id || Math.random().toString(36).substr(2, 9);
            console.log(`Processing activity: ${activity.title}, ID: ${activityId}`);
            
            return {
              id: activityId,
              time: activity.time || '',
              title: activity.title || '',
              category: activity.category || activity.type || 'Other',
              icon: getActivityIcon(activity),
              details: {
                location: activity.details?.location || '',
                description: activity.details?.description || '',
                duration: activity.duration_minutes || 0,
                cost: activity.cost || 0,
                latitude: activity.details?.latitude,
                longitude: activity.details?.longitude
              },
              review_insights: activity.review_insights || null
            };
          }).filter(Boolean);
          
          // Create day message - ALWAYS create it even if no activities
            messages.push({
              id: Date.now() + dayNumber,
              type: 'day',
              dayNumber: dayNumber,
            date: value?.date || '',
            activities: groupActivitiesByCategory(processedActivities)
          });
          
          console.log(`✅ Added day ${dayNumber} message with ${processedActivities.length} activities`);
        });
        
        // Log final count of day messages
        const dayMessages = messages.filter(msg => msg.type === 'day');
        console.log(`Total day messages created: ${dayMessages.length}, days: ${
          dayMessages.map(msg => msg.dayNumber).join(', ')
        }`);
      } else {
        console.warn("❌ No daily_itinerary found in data");
        
        // Fallback: Create days based on trip summary duration
        const tripDuration = itineraryData.trip_summary?.duration_days;
        const defaultDays = tripDuration && tripDuration > 0 ? tripDuration : 1; // Default to 1 day minimum
        
        console.log(`Creating ${defaultDays} default days based on trip duration`);
        
        for (let i = 1; i <= defaultDays; i++) {
          messages.push({
            id: Date.now() + i,
            type: 'day',
            dayNumber: i,
            date: '',
            activities: {}
          });
          console.log(`✅ Added default day ${i} (no activities)`);
        }
      }

      // STEP 6: Sort messages and return
      const sortedMessages = messages.sort((a, b) => {
        if (a.type === 'summary') return -1;
        if (b.type === 'summary') return 1;
        return a.dayNumber - b.dayNumber;
      });
      
      console.log(`Generated ${sortedMessages.length} total messages`);
      console.log(`Day messages: ${sortedMessages.filter(m => m.type === 'day').length}`);
      console.log(`Days included: ${sortedMessages.filter(m => m.type === 'day').map(m => m.dayNumber).join(', ')}`);
      
      if (sortedMessages.length === 0) {
        console.warn("No messages generated, falling back to defaults");
        return createDefaultMessages();
      }
      
      return sortedMessages;
    } catch (error) {
      console.error("Error in parseItineraryToMessages:", error);
      return createDefaultMessages();
    }
  };
  
  // Helper function to create default messages when data is missing or invalid
  const createDefaultMessages = () => {
    console.log("Creating default messages for display");
    
    // Create a basic single day by default
    const defaultMessages = [
      {
        id: Date.now(),
        type: 'summary',
        content: {
          destination: 'Default Destination',
          startDate: new Date().toISOString().split('T')[0],
          endDate: new Date(new Date().getTime() + 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          duration: 1,
          budget: 1000.00
        }
      },
      {
        id: Date.now() + 1,
        type: 'day',
        dayNumber: 1,
        date: new Date().toISOString().split('T')[0],
        activities: {
          'Activities': [
            {
              id: 'default1',
              time: '10:00',
              title: 'Sample Activity',
              category: 'Sightseeing',
              icon: '🏛️',
              details: {
                location: 'Sample Location',
                description: 'This is a sample activity',
                duration: 60,
                cost: 0
              },
              review_insights: null
            }
          ]
        }
      }
    ];
    
    return defaultMessages;
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
                        selectedActivity === activity.id
                          ? "bg-primary/10 shadow-md ring-1 ring-primary"
                          : hoveredActivity === activity.id 
                            ? "bg-white shadow-md ring-1 ring-primary/20" 
                            : "bg-gray-50 hover:bg-gray-100"
                      }`}
                      style={{ 
                        minHeight: (hoveredActivity === activity.id || selectedActivity === activity.id) ? '140px' : 'auto',
                        transform: (hoveredActivity === activity.id || selectedActivity === activity.id) ? 'scale(1.02)' : 'scale(1)'
                      }}
                      onMouseEnter={() => handleActivityHover(activity.id)}
                      onMouseLeave={() => handleActivityHover(null)}
                      onClick={() => {
                        console.log(`Activity clicked with ID: ${activity.id}`, activity);
                        handleActivityClick(activity.id);
                      }}
                    >
                      <div className="flex items-center mb-2">
                        <span className="text-2xl mr-3">{activity.icon}</span>
                        <div>
                          <h5 className="font-medium">{activity.title}</h5>
                          <p className="text-sm text-gray-600">{activity.time}</p>
                        </div>
                        {selectedActivity === activity.id && (
                          <div className="ml-auto">
                            <span className="text-xs font-semibold bg-primary text-white px-2 py-1 rounded-full">
                              Selected
                            </span>
                          </div>
                        )}
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

  // Add effect to propagate day change to parent
  useEffect(() => {
    if (onDayChange && typeof onDayChange === 'function') {
      onDayChange(selectedDay);
    }
  }, [selectedDay, onDayChange]);

  // Update hover state for visual feedback
  const handleActivityHover = (activityId) => {
    setHoveredActivity(activityId);
  };
  
  // Handle activity clicks to center map and show selection
  const handleActivityClick = (activityId) => {
    console.log(`Activity clicked:`, {
      id: activityId,
      type: typeof activityId,
      idLength: activityId ? activityId.toString().length : 0
    });
    
    // Toggle selection if clicking the same activity again
    setSelectedActivity(prev => {
      const newSelection = prev === activityId ? null : activityId;
      console.log(`Selection changed from ${prev} to ${newSelection}`);
      return newSelection;
    });
    
    // If parent provided the onActivityHover callback, call it
    if (onActivityHover && typeof onActivityHover === 'function') {
      console.log(`Calling onActivityHover with ID: ${activityId}`);
      onActivityHover(activityId);
    } else {
      console.warn('onActivityHover callback not provided or not a function');
    }
    
    // Fallback: Try to directly center map using the global function
    // This provides a more reliable communication method between components
    setTimeout(() => {
      try {
        if (window.mapFunctions) {
          // Find any available map instance
          const mapInstanceId = Object.keys(window.mapFunctions)[0];
          if (mapInstanceId && window.mapFunctions[mapInstanceId].centerMapOnActivity) {
            console.log(`Directly calling centerMapOnActivity via window.mapFunctions[${mapInstanceId}]`);
            const result = window.mapFunctions[mapInstanceId].centerMapOnActivity(activityId);
            console.log(`Direct map centering result: ${result ? 'success' : 'failed'}`);
          }
        }
      } catch (error) {
        console.error("Error using direct map centering:", error);
      }
    }, 100); // Short delay to ensure the map component has time to register
  };

  // Loading state
  if (isProcessing) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center text-gray-500">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
          <div className="text-lg font-medium mb-2">Generating Your Itinerary</div>
          <div className="text-sm text-gray-400">This may take a few moments...</div>
          <div className="mt-4 space-y-2">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
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
              // Use the exact data from mock-backend directly without importing
              const mockBackendData = {
                "trip_summary":{
                   "destination":"Los Angeles",
                   "start_date":"2025-06-10",
                   "end_date":"2025-06-13",
                   "duration_days":4,
                   "total_budget":4729.13
                },
                "daily_itinerary":{
                   "day_1":{
                      "date":"2025-06-10",
                      "activities":[
                         {
                            "type":"accommodation",
                            "category":"hotel",
                            "title":"Check-in at The Ritz-Carlton, Los Angeles",
                            "time":"15:00",
                            "duration_minutes":60,
                            "details":{
                               "location":"900 West Olympic Boulevard, Los Angeles",
                               "latitude":34.0452145,
                               "longitude":-118.2666588
                            },
                            "review_insights":{
                               "sentiment":"positive",
                               "strengths":[
                                  "Luxurious and elegant accommodations",
                                  "Exceptional service and attentive staff"
                               ],
                               "weaknesses":[
                                  "Expensive room rates and additional fees"
                               ],
                               "summary":"The Ritz-Carlton, Los Angeles offers a luxurious five-star experience with exceptional service, though guests should be prepared for premium pricing."
                            }
                         },
                         {
                            "type":"dining",
                            "category":"dinner",
                            "title":"Dinner at Eastside Italian Deli",
                            "time":"19:00",
                            "duration_minutes":90,
                            "details":{
                               "location":"1013 Alpine Street, Los Angeles",
                               "latitude":34.0651255,
                               "longitude":-118.2466235
                            },
                            "review_insights":{
                               "sentiment":"positive",
                               "strengths":[
                                  "Authentic Italian sandwiches and food",
                                  "High-quality ingredients and meats"
                               ],
                               "weaknesses":[
                                  "Long lines, especially during lunch hours"
                               ],
                               "summary":"Eastside Italian Deli is a beloved, family-owned Italian deli known for authentic, high-quality sandwiches and imported Italian goods, despite long lines."
                            }
                         }
                      ]
                   },
                   "day_2":{
                      "date":"2025-06-11",
                      "activities":[
                         {
                            "type":"attraction",
                            "category":"theme park",
                            "title":"Visit Universal Studios Hollywood",
                            "time":"09:00",
                            "duration_minutes":480,
                            "details":{
                               "location":"100 Universal City Plaza, Universal City",
                               "latitude":34.1419225,
                               "longitude":-118.358411
                            },
                            "review_insights":{
                               "sentiment":"positive",
                               "strengths":[
                                  "Harry Potter Wizarding World attracts many visitors",
                                  "Super Nintendo World is highly praised for its immersive experience"
                               ],
                               "weaknesses":[
                                  "High ticket prices and expensive food/merchandise",
                                  "Crowds and long wait times, especially on weekends and holidays"
                               ],
                               "summary":"Universal Studios Hollywood offers immersive themed areas like Wizarding World of Harry Potter and Super Nintendo World, alongside high prices and crowds during peak periods."
                            }
                         },
                         {
                            "type":"dining",
                            "category":"dinner",
                            "title":"Dinner at Sushi Gen",
                            "time":"19:00",
                            "duration_minutes":90,
                            "details":{
                               "location":"422 East 2nd Street, Los Angeles",
                               "latitude":34.0467296,
                               "longitude":-118.2387113
                            },
                            "review_insights":{
                               "sentiment":"positive",
                               "strengths":[
                                  "Fresh, high-quality fish",
                                  "Excellent sashimi deluxe lunch special"
                               ],
                               "weaknesses":[
                                  "Long wait times, especially during peak hours",
                                  "Limited seating and crowded dining area"
                               ],
                               "summary":"Sushi Gen is renowned for its exceptionally fresh fish and famous sashimi deluxe lunch special at reasonable prices, despite consistently long wait times."
                            }
                         }
                      ]
                   },
                   "day_3":{
                      "date":"2025-06-12",
                      "activities":[
                         {
                            "type":"attraction",
                            "category":"park",
                            "title":"Visit Griffith Park",
                            "time":"09:00",
                            "duration_minutes":240,
                            "details":{
                               "location":"Los Angeles",
                               "latitude":34.0536909,
                               "longitude":-118.242766
                            },
                            "review_insights":{
                               "sentiment":"positive",
                               "strengths":[
                                  "Breathtaking views of Los Angeles and the Hollywood Sign",
                                  "Extensive hiking trails for all skill levels"
                               ],
                               "weaknesses":[
                                  "Limited parking, especially on weekends and holidays",
                                  "Heavy crowds during peak times"
                               ],
                               "summary":"Griffith Park offers stunning city views, extensive hiking trails, and attractions like the Griffith Observatory, though visitors should arrive early to avoid parking challenges and crowds."
                            }
                         },
                         {
                            "type":"dining",
                            "category":"lunch",
                            "title":"Lunch at Philippe The Original",
                            "time":"12:30",
                            "duration_minutes":90,
                            "details":{
                               "location":"1001 North Alameda Street, Los Angeles",
                               "latitude":34.0596738,
                               "longitude":-118.236941
                            },
                            "review_insights":{
                               "sentiment":"positive",
                               "strengths":[
                                  "Famous French dip sandwiches",
                                  "Historic establishment (opened in 1908)"
                               ],
                               "weaknesses":[
                                  "Long lines during peak hours",
                                  "Limited seating during busy times"
                               ],
                               "summary":"Philippe The Original is a historic Los Angeles landmark famous for inventing the French dip sandwich in 1908, despite occasional long lines."
                            }
                         },
                         {
                            "type":"attraction",
                            "category":"stadium",
                            "title":"Visit Dodger Stadium",
                            "time":"18:00",
                            "duration_minutes":240,
                            "details":{
                               "location":"1000 Vin Scully Ave, Los Angeles",
                               "latitude":34.0736255,
                               "longitude":-118.2398452
                            },
                            "review_insights":{
                               "sentiment":"positive",
                               "strengths":[
                                  "Historic ballpark with iconic views of Los Angeles",
                                  "Great baseball atmosphere and experience"
                               ],
                               "weaknesses":[
                                  "Expensive parking ($30-35)",
                                  "Traffic congestion before and after games"
                               ],
                               "summary":"Dodger Stadium offers an iconic baseball experience with beautiful views, though visitors should plan for expensive parking and traffic congestion."
                            }
                         }
                      ]
                   },
                   "day_4":{
                      "date":"2025-06-13",
                      "activities":[
                         {
                            "type":"attraction",
                            "category":"museum",
                            "title":"Visit The Getty",
                            "time":"09:00",
                            "duration_minutes":240,
                            "details":{
                               "location":"1200 Getty Center Drive, Los Angeles",
                               "latitude":34.0769513,
                               "longitude":-118.475712
                            },
                            "review_insights":{
                               "sentiment":"positive",
                               "strengths":[
                                  "Stunning architecture and views",
                                  "Impressive art collection"
                               ],
                               "weaknesses":[
                                  "Expensive parking ($20-25)",
                                  "Crowded during peak times and weekends"
                               ],
                               "summary":"The Getty offers a world-class cultural experience with stunning architecture and art, though visitors should plan for parking costs and potential crowds."
                            }
                         },
                         {
                            "type":"dining",
                            "category":"lunch",
                            "title":"Lunch at Bottega Louie",
                            "time":"13:00",
                            "duration_minutes":90,
                            "details":{
                               "location":"700 South Grand Avenue, Los Angeles",
                               "latitude":34.047143,
                               "longitude":-118.256605
                            },
                            "review_insights":{
                               "sentiment":"positive",
                               "strengths":[
                                  "High-quality pastries and macarons",
                                  "Beautiful interior and ambiance"
                               ],
                               "weaknesses":[
                                  "Long wait times, especially on weekends",
                                  "Expensive prices"
                               ],
                               "summary":"Bottega Louie is known for its beautiful interior, photogenic desserts, and European-inspired menu, though it can be crowded with long waits and high prices."
                            }
                         },
                         {
                            "type":"transportation",
                            "category":"flight",
                            "title":"Depart Los Angeles on UA505",
                            "time":"18:00",
                            "duration_minutes":101,
                            "details":{
                               "airline":"UA",
                               "flight_number":"UA505",
                               "departure_time":"2025-06-13T06:00:00",
                               "arrival_time":"2025-06-13T07:41:00"
                            }
                         },
                         {
                            "type":"accommodation",
                            "category":"hotel",
                            "title":"Check-out from The Ritz-Carlton, Los Angeles",
                            "time":"12:00",
                            "duration_minutes":30,
                            "details":{
                               "location":"900 West Olympic Boulevard, Los Angeles",
                               "latitude":34.0452145,
                               "longitude":-118.2666588
                            }
                         }
                      ]
                   }
                }
              };

              console.log("Using directly embedded mock data with days:", Object.keys(mockBackendData.daily_itinerary).join(", "));
              processItineraryData(mockBackendData);
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
  console.log("Days filtered from messages:", 
    days.map(day => `Day ${day.dayNumber}`),
    "Total days:", days.length,
    "Raw days data:", JSON.stringify(days.map(d => ({dayNumber: d.dayNumber, id: d.id})))
  );

  // Ensure days are sorted by dayNumber
  days.sort((a, b) => a.dayNumber - b.dayNumber);
  
  // Log after sorting
  console.log("Days after sorting:", days.map(day => `Day ${day.dayNumber}`));

  return (
    <div className="flex flex-col h-full bg-gray-50 max-h-full overflow-hidden">
      {/* Always show summary at the top if available */}
      {itineraryMessages.find(msg => msg.type === 'summary') && (
        <div className="p-4 overflow-y-auto">
          {renderItineraryMessage(itineraryMessages.find(msg => msg.type === 'summary'))}
        </div>
      )}
      
      {days.length > 0 ? (
        <Tab.Group 
          as="div" 
          className="flex flex-col flex-grow overflow-hidden"
          onChange={(index) => {
            // Set selected day based on the tab index
            const newDay = days[index]?.dayNumber || 1;
            console.log(`Changing selected day to ${newDay}`);
            setSelectedDay(newDay);
          }}
        >
          <Tab.List className="flex space-x-2 p-4 bg-white shadow-sm overflow-x-auto">
            {days.map((day) => {
              console.log(`Rendering tab for day ${day.dayNumber}`);
              return (
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
              );
            })}
          </Tab.List>

          <Tab.Panels className="flex-grow overflow-y-auto">
            {days.map((day) => {
              console.log(`Rendering panel for day ${day.dayNumber}`);
              return (
                <Tab.Panel key={day.id} className="h-full overflow-y-auto p-4">
                {renderItineraryMessage(day)}
              </Tab.Panel>
              );
            })}
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