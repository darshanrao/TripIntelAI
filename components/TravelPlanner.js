import React, { useState } from 'react';
import { initiateTravelPlanning, searchFlightsV2, selectFlightsV2, generateItinerary } from '../services/api';
import FlightCard from './FlightCard';

const TravelPlanner = () => {
  // Form state
  const [destination, setDestination] = useState('');
  const [departureDate, setDepartureDate] = useState('');
  const [returnDate, setReturnDate] = useState('');
  const [numTravelers, setNumTravelers] = useState(1);
  
  // Planning state
  const [planningId, setPlanningId] = useState(null);
  const [planningStep, setPlanningStep] = useState('initial'); // initial, searching, selecting, generating, complete
  const [error, setError] = useState(null);
  
  // Flight results
  const [departureFlights, setDepartureFlights] = useState([]);
  const [returnFlights, setReturnFlights] = useState([]);
  const [selectedDepartureFlight, setSelectedDepartureFlight] = useState(null);
  const [selectedReturnFlight, setSelectedReturnFlight] = useState(null);
  
  // Itinerary state
  const [itinerary, setItinerary] = useState(null);

  // Handle form submission to initiate travel planning
  const handleInitiatePlanning = async (e) => {
    e.preventDefault();
    setError(null);
    setPlanningStep('initiating');
    
    try {
      const response = await initiateTravelPlanning(
        destination,
        departureDate,
        returnDate,
        numTravelers
      );
      
      if (response.success) {
        setPlanningId(response.planning_id);
        setPlanningStep('searching');
        
        // Auto search for flights
        await handleSearchFlights(response.planning_id);
      } else {
        setError(response.error || 'Failed to initiate travel planning');
        setPlanningStep('initial');
      }
    } catch (err) {
      setError(err.message || 'An error occurred while initiating travel planning');
      setPlanningStep('initial');
    }
  };

  // Handle flight search
  const handleSearchFlights = async (id) => {
    setError(null);
    setPlanningStep('searching');
    
    try {
      const response = await searchFlightsV2(
        id || planningId,
        destination,
        departureDate,
        returnDate,
        numTravelers
      );
      
      if (response.success && response.data) {
        setDepartureFlights(response.data.departure_flights || []);
        setReturnFlights(response.data.return_flights || []);
        setPlanningStep('selecting');
      } else {
        setError(response.error || 'Failed to find flight options');
        setPlanningStep('initial');
      }
    } catch (err) {
      setError(err.message || 'An error occurred while searching for flights');
      setPlanningStep('initial');
    }
  };

  // Handle flight selection
  const handleSelectFlights = async () => {
    if (!selectedDepartureFlight || !selectedReturnFlight) {
      setError('Please select both departure and return flights');
      return;
    }
    
    setError(null);
    setPlanningStep('selecting-confirm');
    
    try {
      const response = await selectFlightsV2(
        planningId,
        selectedDepartureFlight.id,
        selectedReturnFlight.id
      );
      
      if (response.success) {
        setPlanningStep('generating');
        
        // Auto generate itinerary
        await handleGenerateItinerary();
      } else {
        setError(response.error || 'Failed to confirm flight selection');
        setPlanningStep('selecting');
      }
    } catch (err) {
      setError(err.message || 'An error occurred while selecting flights');
      setPlanningStep('selecting');
    }
  };

  // Handle itinerary generation
  const handleGenerateItinerary = async () => {
    setError(null);
    setPlanningStep('generating');
    
    try {
      const response = await generateItinerary(
        planningId,
        selectedDepartureFlight.id,
        selectedReturnFlight.id
      );
      
      if (response.success && response.data) {
        setItinerary(response.data.itinerary);
        setPlanningStep('complete');
      } else {
        setError(response.error || 'Failed to generate itinerary');
        setPlanningStep('selecting');
      }
    } catch (err) {
      setError(err.message || 'An error occurred while generating your itinerary');
      setPlanningStep('selecting');
    }
  };

  // Select a departure flight
  const selectDepartureFlight = (flight) => {
    setSelectedDepartureFlight(flight);
  };

  // Select a return flight
  const selectReturnFlight = (flight) => {
    setSelectedReturnFlight(flight);
  };

  // Reset the form
  const handleReset = () => {
    setDestination('');
    setDepartureDate('');
    setReturnDate('');
    setNumTravelers(1);
    setPlanningId(null);
    setPlanningStep('initial');
    setError(null);
    setDepartureFlights([]);
    setReturnFlights([]);
    setSelectedDepartureFlight(null);
    setSelectedReturnFlight(null);
    setItinerary(null);
  };

  // Render appropriate content based on planning step
  const renderContent = () => {
    switch (planningStep) {
      case 'initial':
        return (
          <form onSubmit={handleInitiatePlanning} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Destination</label>
              <input
                type="text"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary"
                placeholder="e.g. Tokyo, Japan"
                required
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Departure Date</label>
                <input
                  type="date"
                  value={departureDate}
                  onChange={(e) => setDepartureDate(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Return Date</label>
                <input
                  type="date"
                  value={returnDate}
                  onChange={(e) => setReturnDate(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary"
                  required
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700">Number of Travelers</label>
              <input
                type="number"
                min="1"
                max="10"
                value={numTravelers}
                onChange={(e) => setNumTravelers(parseInt(e.target.value))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary"
                required
              />
            </div>
            
            <button
              type="submit"
              className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
            >
              Start Planning
            </button>
          </form>
        );
        
      case 'initiating':
      case 'searching':
        return (
          <div className="py-8 text-center">
            <div className="flex justify-center mb-4">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
            </div>
            <p className="text-gray-600">
              {planningStep === 'initiating' ? 'Initiating your travel plan...' : 'Searching for flights...'}
            </p>
          </div>
        );
        
      case 'selecting':
        return (
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Select Your Flights</h3>
            
            <div className="mb-6">
              <h4 className="text-md font-medium text-gray-700 mb-2">Departure Flights</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {departureFlights.map((flight) => (
                  <div 
                    key={flight.id}
                    className={`border rounded-lg p-2 cursor-pointer ${
                      selectedDepartureFlight?.id === flight.id ? 'border-primary bg-blue-50' : 'border-gray-200'
                    }`}
                    onClick={() => selectDepartureFlight(flight)}
                  >
                    <FlightCard flight={flight} index={0} onSelect={() => selectDepartureFlight(flight)} />
                  </div>
                ))}
              </div>
            </div>
            
            <div className="mb-6">
              <h4 className="text-md font-medium text-gray-700 mb-2">Return Flights</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {returnFlights.map((flight) => (
                  <div 
                    key={flight.id}
                    className={`border rounded-lg p-2 cursor-pointer ${
                      selectedReturnFlight?.id === flight.id ? 'border-primary bg-blue-50' : 'border-gray-200'
                    }`}
                    onClick={() => selectReturnFlight(flight)}
                  >
                    <FlightCard flight={flight} index={0} onSelect={() => selectReturnFlight(flight)} />
                  </div>
                ))}
              </div>
            </div>
            
            <div className="flex justify-between">
              <button
                onClick={handleReset}
                className="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
              >
                Start Over
              </button>
              <button
                onClick={handleSelectFlights}
                disabled={!selectedDepartureFlight || !selectedReturnFlight}
                className={`py-2 px-4 border border-transparent rounded-md text-sm font-medium text-white 
                  ${(!selectedDepartureFlight || !selectedReturnFlight) ? 
                    'bg-gray-300 cursor-not-allowed' : 
                    'bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary'
                  }`}
              >
                Confirm Selection
              </button>
            </div>
          </div>
        );
        
      case 'selecting-confirm':
      case 'generating':
        return (
          <div className="py-8 text-center">
            <div className="flex justify-center mb-4">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
            </div>
            <p className="text-gray-600">
              {planningStep === 'selecting-confirm' ? 'Confirming your flight selection...' : 'Generating your itinerary...'}
            </p>
          </div>
        );
        
      case 'complete':
        return (
          <div>
            <div className="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-green-700">
                    Your travel plan is ready! Check the itinerary view for details.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-2">Trip Summary</h3>
              <div className="bg-white shadow overflow-hidden sm:rounded-lg">
                <div className="border-t border-gray-200 px-4 py-5 sm:p-0">
                  <dl className="sm:divide-y sm:divide-gray-200">
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                      <dt className="text-sm font-medium text-gray-500">Destination</dt>
                      <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        {itinerary?.trip_summary?.destination || destination}
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                      <dt className="text-sm font-medium text-gray-500">Dates</dt>
                      <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        {itinerary?.trip_summary?.start_date || departureDate} to {itinerary?.trip_summary?.end_date || returnDate}
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                      <dt className="text-sm font-medium text-gray-500">Duration</dt>
                      <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        {itinerary?.trip_summary?.duration_days || 'Not specified'} days
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                      <dt className="text-sm font-medium text-gray-500">Total Budget</dt>
                      <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        ${itinerary?.trip_summary?.total_budget?.toFixed(2) || 'Not specified'}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
            </div>
            
            <div className="flex justify-between">
              <button
                onClick={handleReset}
                className="py-2 px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
              >
                Plan Another Trip
              </button>
              <button
                onClick={() => window.location.href = '/itinerary'} 
                className="py-2 px-4 border border-transparent rounded-md text-sm font-medium text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
              >
                View Full Itinerary
              </button>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Plan Your Trip</h2>
      
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">
                {error}
              </p>
            </div>
          </div>
        </div>
      )}
      
      {renderContent()}
    </div>
  );
};

export default TravelPlanner; 