import { useState, useEffect, useRef, useCallback } from 'react';
import { GoogleMap, useJsApiLoader, Marker, DirectionsRenderer } from '@react-google-maps/api';
import { motion } from 'framer-motion';

const containerStyle = {
  width: '100%',
  height: '100%'
};

const defaultCenter = {
  lat: 40.7580, 
  lng: -73.9855
};

const MapView = ({ activities, day }) => {
  const [map, setMap] = useState(null);
  const [directions, setDirections] = useState(null);
  const [mapCenter, setMapCenter] = useState(defaultCenter);
  const [isLoading, setIsLoading] = useState(true);
  const [markers, setMarkers] = useState([]);
  const directionsServiceRef = useRef(null);
  const directionsRendererRef = useRef(null);

  // Load the Google Maps API
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || 'YOUR_API_KEY_HERE', // Replace with your API key
    libraries: ['places', 'directions']
  });

  // Set up map markers from activities
  useEffect(() => {
    if (activities && activities.length > 0) {
      setMarkers(activities.map((activity, index) => ({
        id: index,
        position: activity.location,
        title: activity.title,
        icon: activity.icon
      })));

      // Set map center to first activity
      if (activities[0]?.location) {
        setMapCenter(activities[0].location);
      }
    }
  }, [activities]);

  // Calculate and display directions when activities change
  useEffect(() => {
    if (isLoaded && activities && activities.length > 1) {
      calculateRoute();
    }
  }, [isLoaded, activities, day]);

  // Map load handler
  const onLoad = useCallback(function callback(map) {
    setMap(map);
    setIsLoading(false);
  }, []);

  // Map unmount handler
  const onUnmount = useCallback(function callback() {
    setMap(null);
  }, []);

  // Calculate the route between all activity locations
  const calculateRoute = () => {
    if (!window.google) return;
    
    setIsLoading(true);
    
    // Create directions service if needed
    if (!directionsServiceRef.current) {
      directionsServiceRef.current = new window.google.maps.DirectionsService();
    }
    
    // Extract waypoints (skip first and last locations)
    const waypoints = activities.slice(1, -1).map(activity => ({
      location: activity.location,
      stopover: true
    }));
    
    // Create request for directions
    const request = {
      origin: activities[0].location,
      destination: activities[activities.length - 1].location,
      waypoints: waypoints,
      optimizeWaypoints: true,
      travelMode: window.google.maps.TravelMode.DRIVING
    };
    
    // Request directions
    directionsServiceRef.current.route(request, (result, status) => {
      if (status === window.google.maps.DirectionsStatus.OK) {
        setDirections(result);
      } else {
        console.error(`Directions request failed: ${status}`);
      }
      setIsLoading(false);
    });
  };

  // Render loading state
  if (!isLoaded || isLoading) {
    return (
      <div className="flex h-full bg-gray-100 items-center justify-center">
        <div className="flex flex-col items-center">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-4 text-gray-600">Loading map...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (loadError) {
    return (
      <div className="flex h-full bg-gray-100 items-center justify-center">
        <div className="text-center p-4">
          <p className="text-red-500">Error loading maps</p>
          <p className="text-sm text-gray-600 mt-2">
            Please check your internet connection and try again
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Map header */}
      <div className="bg-gray-100 p-4 shadow-sm">
        <h2 className="text-lg font-semibold">Day {day} Route</h2>
        {activities.length > 0 && (
          <p className="text-sm text-gray-600 mt-1">
            {activities.length} locations • {activities.length - 1} stops
          </p>
        )}
      </div>
      
      {/* Map container */}
      <motion.div 
        className="flex-1 relative"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
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
          {/* Display route if directions are available */}
          {directions && (
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
          {markers.map((marker) => (
            <Marker
              key={marker.id}
              position={marker.position}
              title={marker.title}
              label={{
                text: marker.icon,
                fontSize: '16px'
              }}
            />
          ))}
        </GoogleMap>
      </motion.div>
    </div>
  );
};

export default MapView; 