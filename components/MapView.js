import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { GoogleMap, useJsApiLoader, Marker, DirectionsRenderer } from '@react-google-maps/api';
import { motion } from 'framer-motion';

// Track component instances to avoid duplicate operations
let instanceCounter = 0;

const containerStyle = {
  width: '100%',
  height: '100%'
};

const defaultCenter = {
  lat: 34.0522, // Los Angeles coordinates as default
  lng: -118.2437
};

// Define libraries array as a constant outside the component
// This prevents the "LoadScript has been reloaded unintentionally" warning
// React performance warning occurs when passing a new array on each render
const GOOGLE_MAPS_LIBRARIES = ['places'];

// Track if Google Maps has been loaded globally
let googleMapsLoaded = false;

// Maps icon based on activity type/category
const getMarkerIcon = (activity) => {
  const type = activity.type?.toLowerCase() || '';
  const category = activity.category?.toLowerCase() || '';
  
  if (type.includes('dining') || category.includes('food') || category.includes('lunch') || 
      category.includes('dinner') || category.includes('breakfast')) {
    return '🍽️';
  }
  if (type.includes('attraction') || category.includes('museum') || category.includes('gallery') || 
      category.includes('landmark') || category.includes('park')) {
    return '🏛️';
  }
  if (type.includes('transportation')) {
    return '✈️';
  }
  if (type.includes('accommodation') || category.includes('hotel')) {
    return '🏨';
  }
  // Default icon
  return '📍';
};

const MapView = ({ 
  activities, 
  day, 
  itineraryData, 
  selectedDay,
  calculateRoutes = false, // Add prop to control route calculation, default to false
  hoveredActivityId = null  // New prop to track hovered activity in the list
}) => {
  const [map, setMap] = useState(null);
  const [directions, setDirections] = useState(null);
  const [mapCenter, setMapCenter] = useState(defaultCenter);
  const [isLoading, setIsLoading] = useState(true);
  const [markers, setMarkers] = useState([]);
  const [mapsLoaded, setMapsLoaded] = useState(false);
  const [selectedMarkerId, setSelectedMarkerId] = useState(null);
  const directionsServiceRef = useRef(null);
  const directionsRendererRef = useRef(null);
  const scriptRef = useRef(null);
  const initializationAttempted = useRef(false);
  
  // Track component instance for debugging
  const instanceId = useRef(`map-${++instanceCounter}`);
  const processingRef = useRef(false); // Track if we're currently processing
  const activitiesRef = useRef([]); // Store previous activities to avoid duplicate processing
  const routeCalculatedRef = useRef(false); // Track if we've already calculated routes
  const markersRef = useRef([]);  // Keep a stable reference to markers
  const markerRenderCountRef = useRef(0); // Track marker render count
  
  // Helper function to log with instance ID
  const logWithId = useCallback((message, ...args) => {
    console.log(`[${instanceId.current}] ${message}`, ...args);
  }, []);

  // Direct function to center map on a specific activity ID
  // This is more reliable than relying on prop changes
  const centerMapOnActivity = useCallback((activityId) => {
    if (!map || !activityId || markers.length === 0) {
      logWithId(`centerMapOnActivity called but cannot center yet. Map: ${!!map}, ActivityID: ${activityId}, Markers: ${markers.length}`);
      return false;
    }
    
    logWithId(`centerMapOnActivity called with ID: ${activityId}`);
    
    // First try direct ID match
    let marker = markers.find(m => m.id === activityId);
    
    // If not found, try activity ID match
    if (!marker) {
      marker = markers.find(m => m.activity && m.activity.id === activityId);
    }
    
    // If still not found, try string comparison
    if (!marker) {
      marker = markers.find(m => 
        String(m.id) === String(activityId) || 
        (m.activity && String(m.activity.id) === String(activityId))
      );
    }
    
    if (marker && marker.position) {
      logWithId(`Directly centering map on: ${marker.title}`);
      setSelectedMarkerId(marker.id);
      map.panTo(marker.position);
      map.setZoom(15);
      return true;
    } else {
      logWithId(`Could not find marker for direct centering: ${activityId}`);
      console.log("Available marker IDs:", markers.map(m => m.id).join(', '));
      return false;
    }
  }, [map, markers, logWithId]);

  // Expose the centerMapOnActivity function via window for direct access
  // This can be used as a bridge between components when props aren't working
  useEffect(() => {
    if (!window.mapFunctions) {
      window.mapFunctions = {};
    }
    window.mapFunctions[instanceId.current] = {
      centerMapOnActivity
    };
    
    return () => {
      if (window.mapFunctions && window.mapFunctions[instanceId.current]) {
        delete window.mapFunctions[instanceId.current];
      }
    };
  }, [instanceId, centerMapOnActivity]);

  // Load the Google Maps API script securely
  useEffect(() => {
    logWithId("Initializing MapView");
    
    async function loadGoogleMapsScript() {
      try {
        logWithId("Setting up Google Maps...");
        
        // Check if already loaded globally
        if (googleMapsLoaded || window.google?.maps) {
          logWithId("Google Maps already loaded globally");
          setMapsLoaded(true);
          setIsLoading(false);
          return;
        }
        
        // If script is already being loaded by another instance
        if (document.querySelector('script[src*="maps.googleapis.com"]')) {
          logWithId("Google Maps script already being loaded by another instance");
          // Wait for the existing script to finish loading
          const checkGoogleMaps = setInterval(() => {
            if (window.google?.maps) {
              clearInterval(checkGoogleMaps);
              setMapsLoaded(true);
              setIsLoading(false);
              googleMapsLoaded = true;
            }
          }, 300);
          return;
        }

        // Only create script if we're the first to try loading the API
        if (!scriptRef.current && !initializationAttempted.current) {
          initializationAttempted.current = true;
          
          // Fetch API key from secure endpoint
          const response = await fetch('/api/map-key');
          const data = await response.json();
          
          if (!data.key) {
            console.error('Map API key not available');
            return;
          }
          
          // Create script element to load Google Maps
          const script = document.createElement('script');
          // Use loading=async to improve performance and prevent warnings
          script.src = `https://maps.googleapis.com/maps/api/js?key=${data.key}&libraries=places&callback=initGoogleMaps&loading=async`;
          script.async = true;
          script.defer = true;
          scriptRef.current = script;
          
          // Create global callback that will be called by Google Maps once loaded
          window.initGoogleMaps = () => {
            logWithId("Google Maps initialized");
            setMapsLoaded(true);
            setIsLoading(false);
            googleMapsLoaded = true;
            // Clean up callback to prevent memory leaks
            delete window.initGoogleMaps;
          };
          
          // Append script to document
          document.head.appendChild(script);
        }
      } catch (error) {
        console.error('Error setting up Google Maps:', error);
      }
    }
    
    loadGoogleMapsScript();
    
    // Cleanup function
    return () => {
      logWithId("Cleaning up MapView");
      // Reset our route calculation flag
      routeCalculatedRef.current = false;
      // We should not remove the script if it's used by other components
      // Only cleanup if we're the last component using Google Maps
      if (scriptRef.current && document.querySelectorAll('[data-map-container="true"]').length <= 1) {
        if (document.head.contains(scriptRef.current)) {
          document.head.removeChild(scriptRef.current);
          scriptRef.current = null;
        }
      }
      
      // Clean up window functions
      if (window.initGoogleMaps) {
        delete window.initGoogleMaps;
      }
    };
  }, []); // Only run on mount and unmount

  // Create a stable currentDay value
  const currentDay = useMemo(() => `day_${selectedDay || day || 1}`, [selectedDay, day]);

  // Process the itinerary data to extract activity markers for the current day
  useEffect(() => {
    // Skip if already processing to avoid multiple concurrent calls
    if (processingRef.current) {
      logWithId("Already processing activities, skipping");
      return;
    }
    
    processingRef.current = true;
    
    // Reset route calculation flag when day changes
    routeCalculatedRef.current = false;
    
    // Function to process after a short delay to debounce rapid changes
    const processWithDelay = setTimeout(() => {
      // Direct handling for activities array passed to component
      if (Array.isArray(activities) && activities.length > 0) {
        // Convert activities to a stable string representation for comparison
        const activityHash = JSON.stringify(activities.map(a => ({ 
          id: a.id || a.title,
          title: a.title,
          lat: a.details?.latitude || a.location?.lat,
          lng: a.details?.longitude || a.location?.lng
        })));
        
        // Only process if activities have changed
        const prevActivityHash = JSON.stringify(activitiesRef.current);
        if (activityHash !== prevActivityHash) {
          logWithId(`Processing ${activities.length} activities`);
          processActivitiesArray(activities);
          activitiesRef.current = activityHash;
        } else {
          logWithId("Activities unchanged, skipping processing");
        }
      } 
      // Process from itineraryData if available
      else if (itineraryData && itineraryData.daily_itinerary) {
        logWithId(`Looking for activities in itineraryData for ${currentDay}`);
        
        const dayData = itineraryData.daily_itinerary[currentDay];
        
        if (dayData && Array.isArray(dayData.activities) && dayData.activities.length > 0) {
          // Convert activities to a stable string representation for comparison
          const activityHash = JSON.stringify(dayData.activities.map(a => ({ 
            id: a.id || a.title,
            title: a.title,
            lat: a.details?.latitude,
            lng: a.details?.longitude
      })));

          // Only process if activities have changed
          const prevActivityHash = JSON.stringify(activitiesRef.current);
          if (activityHash !== prevActivityHash) {
            logWithId(`Processing ${dayData.activities.length} activities from itineraryData`);
            processActivitiesArray(dayData.activities);
            activitiesRef.current = activityHash;
          } else {
            logWithId("Activities from itineraryData unchanged, skipping processing");
          }
        } else {
          logWithId(`No valid activities found for ${currentDay}`);
          setMarkers([]);
          markersRef.current = [];
          activitiesRef.current = [];
        }
      } else if (!activities) {
        logWithId("No activities or itineraryData available for map");
        setMarkers([]);
        markersRef.current = [];
        activitiesRef.current = [];
      }
      
      processingRef.current = false;
    }, 200); // 200ms debounce
    
    return () => {
      clearTimeout(processWithDelay);
      processingRef.current = false;
    };
  }, [activities, itineraryData, currentDay, logWithId]);

  // Function to process activities and extract markers
  const processActivitiesArray = useCallback((activitiesArray) => {
    logWithId(`Processing ${activitiesArray.length} activities for map markers`);

    const extractedMarkers = [];
    let validLocations = 0;
    
    activitiesArray.forEach((activity, index) => {
      if (!activity) return;
      
      // Log activity for debugging
      console.log(`Processing activity ${index}:`, {
        id: activity.id || 'undefined',
        title: activity.title,
        location: activity.details?.location,
        lat: activity.details?.latitude || activity.location?.lat,
        lng: activity.details?.longitude || activity.location?.lng
      });
      
      // Ensure activity has an ID - this is crucial for matching later
      if (!activity.id) {
        activity.id = `generated-${Math.random().toString(36).substr(2, 9)}`;
        console.log(`Generated ID for activity "${activity.title}": ${activity.id}`);
      }
      
      // Extract the latitude and longitude directly from activity details
      let lat, lng;
      
      // Try multiple possible data structures for coordinates
      if (activity.details?.latitude && activity.details?.longitude) {
        // Direct lat/lng from activity details
        lat = typeof activity.details.latitude === 'string' 
          ? parseFloat(activity.details.latitude) 
          : activity.details.latitude;
        lng = typeof activity.details.longitude === 'string' 
          ? parseFloat(activity.details.longitude) 
          : activity.details.longitude;
      } else if (activity.location?.lat && activity.location?.lng) {
        // Already formatted location object
        lat = typeof activity.location.lat === 'string' 
          ? parseFloat(activity.location.lat) 
          : activity.location.lat;
        lng = typeof activity.location.lng === 'string' 
          ? parseFloat(activity.location.lng) 
          : activity.location.lng;
      } else if (activity.details?.location?.lat && activity.details?.location?.lng) {
        // Nested location object
        lat = typeof activity.details.location.lat === 'string' 
          ? parseFloat(activity.details.location.lat) 
          : activity.details.location.lat;
        lng = typeof activity.details.location.lng === 'string' 
          ? parseFloat(activity.details.location.lng) 
          : activity.details.location.lng;
      } else if (typeof activity.details?.location === 'string' && activity.details?.location) {
        // If location is a string, we can't extract coordinates
        logWithId(`Activity has string location but no coordinates: "${activity.details.location}"`);
      } else {
        // No valid location data found
        logWithId(`No location data for activity: ${activity.title || 'Unknown'}`);
      }
      
      // Skip if no valid coordinates
      if (isNaN(lat) || isNaN(lng) || lat === 0 || lng === 0) {
        return;
      }
      
      validLocations++;
      
      // Create marker with the activity object included for reference
      // IMPORTANT: Use the exact same activity.id for the marker.id
      const marker = {
        id: activity.id, // Use the exact same ID from the activity
        position: { lat, lng },
        title: activity.title || 'Unknown Location',
        icon: getMarkerIcon(activity),
        activity: activity  // Store the entire activity object for reference
      };
      
      // Log generated marker for debugging
      console.log(`Created marker for ${activity.title}:`, {
        id: marker.id,
        activityId: activity.id,
        title: marker.title,
        position: marker.position
      });
      
      extractedMarkers.push(marker);
    });
    
    logWithId(`Created ${extractedMarkers.length} map markers (${validLocations} valid locations)`);
    
    // Only update markers if something has changed to prevent unnecessary re-renders
    const markersChanged = JSON.stringify(extractedMarkers) !== JSON.stringify(markersRef.current);
    if (markersChanged) {
      // Reset route calculation flag if markers have changed
      routeCalculatedRef.current = false;
      markersRef.current = extractedMarkers;
      // Update markers state
      setMarkers(extractedMarkers);
      
      // Set map center to first marker if available
      if (extractedMarkers.length > 0) {
        setMapCenter(extractedMarkers[0].position);
      } else {
        // Default to Los Angeles if no markers
        setMapCenter(defaultCenter);
      }
    } else {
      logWithId("Markers haven't changed, skipping update");
    }
  }, [logWithId]);

  // Calculate and display directions when markers change - only if calculateRoutes is true
  useEffect(() => {
    // Skip route calculation if feature is disabled via props
    if (!calculateRoutes) {
      return;
    }
    
    // Only calculate routes if we have Google Maps loaded, a map instance, and multiple markers,
    // and we haven't calculated routes yet for these markers
    if (mapsLoaded && map && markers.length > 1 && !routeCalculatedRef.current) {
      // Debounce to avoid multiple rapid calls
      const calculateTimer = setTimeout(() => {
        logWithId(`Calculating route for ${markers.length} markers`);
      calculateRoute();
        // Mark that we've calculated routes for these markers
        routeCalculatedRef.current = true;
      }, 500); // 500ms debounce
      
      return () => clearTimeout(calculateTimer);
    }
  }, [mapsLoaded, map, markers, calculateRoutes]);

  // Map load handler - memoized to prevent recreation on renders
  const onLoad = useCallback((map) => {
    logWithId("Map loaded successfully");
    setMap(map);
    
    // Initialize directionsService only if route calculation is enabled
    if (calculateRoutes && window.google?.maps && !directionsServiceRef.current) {
      logWithId("Initializing directions service on map load");
      directionsServiceRef.current = new window.google.maps.DirectionsService();
    }
    
    // If we already have markers, set bounds to fit all markers
    if (markers.length > 0) {
      try {
        const bounds = new window.google.maps.LatLngBounds();
        markers.forEach(marker => {
          if (marker.position && marker.position.lat && marker.position.lng) {
            bounds.extend(marker.position);
          }
        });
        
        // Only adjust bounds if we have valid markers
        if (!bounds.isEmpty()) {
          map.fitBounds(bounds);
          
          // Zoom out slightly if we only have one marker
          if (markers.length === 1) {
            map.setZoom(15);
          }
        } else {
          // If bounds is empty, center on default position
          map.setCenter(defaultCenter);
          map.setZoom(12);
        }
      } catch (error) {
        console.error("Error setting map bounds:", error);
        // Fall back to default center if there's an error
        map.setCenter(defaultCenter);
        map.setZoom(12);
      }
    } else {
      // No markers, center on default
      map.setCenter(defaultCenter);
      map.setZoom(12);
    }
    
    setIsLoading(false);
  }, [markers, calculateRoutes]);

  // Map unmount handler
  const onUnmount = useCallback(() => {
    logWithId("Map unmounted");
    setMap(null);
  }, [logWithId]);

  // Calculate the route between all markers
  const calculateRoute = useCallback(() => {
    // Skip if route calculation is disabled
    if (!calculateRoutes) {
      return;
    }
    
    // Skip if we've already calculated a route for these markers
    if (routeCalculatedRef.current) {
      logWithId("Route already calculated for these markers, skipping");
      return;
    }
    
    if (!window.google || !window.google.maps) {
      logWithId("Google Maps API not loaded yet");
      return;
    }
    
    // Ensure directions service was successfully created
    if (!directionsServiceRef.current) {
      logWithId("Directions service not available");
      return;
    }
    
    if (markers.length < 2) {
      logWithId("Need at least 2 markers for directions");
      return;
    }
    
    setIsLoading(true);
    
    // Extract waypoints (skip first and last locations)
    const waypoints = markers.slice(1, -1).map(marker => ({
      location: marker.position,
      stopover: true
    }));
    
    // Create request for directions
    const request = {
      origin: markers[0].position,
      destination: markers[markers.length - 1].position,
      waypoints: waypoints,
      optimizeWaypoints: true,
      travelMode: window.google.maps.TravelMode.DRIVING
    };
    
    // Request directions
    directionsServiceRef.current.route(request, (result, status) => {
      if (status === window.google.maps.DirectionsStatus.OK) {
        logWithId("Route calculated successfully");
        setDirections(result);
        // Mark that we've calculated routes for these markers
        routeCalculatedRef.current = true;
      } else {
        console.error(`Directions request failed: ${status}`);
        // Clear any previous directions if the request fails
        setDirections(null);
      }
      setIsLoading(false);
    });
  }, [markers, logWithId, calculateRoutes]);

  // Keep track of marker render count to help identify rendering issues
  useEffect(() => {
    markerRenderCountRef.current += 1;
    logWithId(`Markers rendered (count: ${markerRenderCountRef.current})`);
  }, [markers, logWithId]);

  // Center map on selected activity (triggered by click in ItineraryView)
  useEffect(() => {
    if (!hoveredActivityId) return;
    logWithId(`Received new hoveredActivityId: ${hoveredActivityId} (type: ${typeof hoveredActivityId})`);
    
    // Log all IDs for comparison
    console.log("All marker IDs:", markers.map(m => ({
      id: m.id,
      activityId: m.activity?.id,
      title: m.title
    })));
    
    // Use our direct centering function
    const centered = centerMapOnActivity(hoveredActivityId);
    
    if (!centered) {
      logWithId(`Could not center using normal method, will retry when map/markers are ready`);
      
      // Try using direct ID matching
      let found = false;
      markers.forEach(marker => {
        // Check every possible match
        if (
          marker.id === hoveredActivityId ||
          String(marker.id) === String(hoveredActivityId) ||
          (marker.activity && marker.activity.id === hoveredActivityId) ||
          (marker.activity && String(marker.activity.id) === String(hoveredActivityId))
        ) {
          logWithId(`Found marker match through direct comparison: ${marker.title}`);
          setSelectedMarkerId(marker.id);
          if (map) {
            map.panTo(marker.position);
            map.setZoom(15);
            found = true;
          }
        }
      });
      
      if (!found) {
        // As last resort, try matching by title substring
        const matchByTitle = markers.find(m => 
          m.title && m.title.includes(hoveredActivityId) || 
          (m.activity && m.activity.title && m.activity.title.includes(hoveredActivityId))
        );
        
        if (matchByTitle && map) {
          logWithId(`Found marker by title match: ${matchByTitle.title}`);
          setSelectedMarkerId(matchByTitle.id);
          map.panTo(matchByTitle.position);
          map.setZoom(15);
        } else {
          // Store the ID to try again when the map and markers are ready
          const retryTimer = setTimeout(() => {
            if (map && markers.length > 0) {
              logWithId(`Retrying centering for activity ${hoveredActivityId}`);
              centerMapOnActivity(hoveredActivityId);
            }
          }, 500); // Wait a bit and try again
          
          return () => clearTimeout(retryTimer);
        }
      }
    }
  }, [hoveredActivityId, centerMapOnActivity, map, markers, logWithId]);

  // Render loading state
  if (!mapsLoaded || isLoading) {
    return (
      <div className="flex h-full bg-gray-100 items-center justify-center">
        <div className="flex flex-col items-center">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-4 text-gray-600">Loading map...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Map header */}
      <div className="bg-gray-100 p-4 shadow-sm">
        <h2 className="text-lg font-semibold">Day {selectedDay || day || 1} Map</h2>
        {markers.length > 0 ? (
          <p className="text-sm text-gray-600 mt-1">
            {markers.length} locations • {calculateRoutes && markers.length > 1 ? `${markers.length - 1} stops` : 'No route'}
          </p>
        ) : (
          <p className="text-sm text-gray-600 mt-1">No locations with map coordinates for this day</p>
        )}
      </div>
      
      {/* Map container */}
      <motion.div 
        className="flex-1 relative"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        data-map-container="true"
      >
        {mapsLoaded && window.google && (
        <GoogleMap
          mapContainerStyle={containerStyle}
          center={mapCenter}
          zoom={12}
          onLoad={onLoad}
          onUnmount={onUnmount}
          options={{
            zoomControl: true,
            streetViewControl: false,
            mapTypeControl: false,
            fullscreenControl: true,
          }}
        >
            {/* Display route if directions are available and route calculation is enabled */}
            {calculateRoutes && directions && (
            <DirectionsRenderer
              options={{
                directions: directions,
                suppressMarkers: true, // We'll add our own markers
                polylineOptions: {
                  strokeColor: '#4a90e2',
                  strokeWeight: 5,
                  strokeOpacity: 0.7,
                  className: 'route-path', // For animation
                }
              }}
            />
          )}
          
          {/* Display markers for each activity */}
          {markers.map((marker) => {
            // Check if marker should have animation - handle different animation availability
            let markerAnimation = null;
            if (selectedMarkerId === marker.id && window.google && window.google.maps) {
              markerAnimation = window.google.maps.Animation.BOUNCE;
            }
            
            // Debug marker properties
            console.log(`Rendering marker: ${marker.title}, ID: ${marker.id}, activityID: ${marker.activity?.id}`);
            
            return (
              <Marker
                key={marker.id}
                position={marker.position}
                title={marker.title}
                animation={markerAnimation}
                label={{
                  text: marker.icon,
                  className: selectedMarkerId === marker.id ? 'text-lg' : '',
                }}
                onClick={() => {
                  // Set this marker as selected
                  logWithId(`Marker clicked: ${marker.title} (ID: ${marker.id})`);
                  setSelectedMarkerId(marker.id);
                  
                  // Zoom in and center on clicked marker
                  if (map) {
                    map.setZoom(16);
                    map.panTo(marker.position);
                  }
                }}
              />
            );
          })}
        </GoogleMap>
        )}
      </motion.div>
    </div>
  );
};

export default MapView; 