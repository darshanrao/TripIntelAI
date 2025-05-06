import React from 'react';
import { FaPlaneDeparture, FaPlaneArrival, FaClock, FaMoneyBillWave, FaSuitcase, FaChair } from 'react-icons/fa';
import { motion } from 'framer-motion';

const FlightCard = ({ flight, index, onSelect }) => {
  // Extract flight data
  const { 
    id,
    airline, 
    flight_number: flightNumber, 
    departure_time: departureTime, 
    arrival_time: arrivalTime,
    departure_airport,
    arrival_airport,
    departure_city,
    arrival_city,
    price, 
    currency = 'USD',
    duration_minutes,
    cabin_class,
    baggage_included
  } = flight;

  // Format date and time
  const formatDateTime = (dateTimeStr) => {
    try {
      const date = new Date(dateTimeStr);
      return {
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        time: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
      };
    } catch (e) {
      // If parsing fails, return the original string
      return { date: 'N/A', time: dateTimeStr };
    }
  };
  
  const departure = formatDateTime(departureTime);
  const arrival = formatDateTime(arrivalTime);
  
  // Calculate flight duration (if available)
  let duration = '';
  if (duration_minutes) {
    const hours = Math.floor(duration_minutes / 60);
    const minutes = duration_minutes % 60;
    duration = `${hours}h ${minutes}m`;
  } else {
    try {
      if (departureTime && arrivalTime) {
        const deptTime = new Date(departureTime);
        const arrTime = new Date(arrivalTime);
        const durationMs = arrTime - deptTime;
        const hours = Math.floor(durationMs / (1000 * 60 * 60));
        const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
        duration = `${hours}h ${minutes}m`;
      }
    } catch (e) {
      duration = 'N/A';
    }
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="bg-white rounded-lg shadow overflow-hidden hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onSelect(id || index)}
    >
      <div className="p-2">
        {/* Airline and price */}
        <div className="flex justify-between items-center mb-1 text-sm">
          <div className="font-semibold text-primary">
            {airline} {flightNumber}
          </div>
          <div className="font-bold text-green-600">
            ${typeof price === 'number' ? price.toFixed(0) : price}
          </div>
        </div>
        
        {/* Flight route and time */}
        <div className="flex justify-between text-xs mb-1">
          <div className="text-center">
            <div className="font-bold">{departure.time}</div>
            <div className="text-gray-600">{departure_airport}</div>
          </div>
          
          <div className="flex flex-col items-center px-1">
            <div className="text-gray-500 text-[10px]">{duration}</div>
            <div className="w-full flex items-center">
              <div className="h-[1px] w-10 bg-gray-300"></div>
              <div className="px-1 text-xs">✈️</div>
              <div className="h-[1px] w-10 bg-gray-300"></div>
            </div>
          </div>
          
          <div className="text-center">
            <div className="font-bold">{arrival.time}</div>
            <div className="text-gray-600">{arrival_airport}</div>
          </div>
        </div>
        
        {/* Flight extras */}
        <div className="flex justify-between items-center text-[10px] text-gray-500 mb-1">
          <div>
            {departure.date}
          </div>
          <div className="flex items-center">
            <FaChair className="mr-1" />{cabin_class}
            {baggage_included && <><span className="mx-1">•</span><FaSuitcase /></>}
          </div>
        </div>
        
        <button 
          className="w-full py-1 bg-primary text-white rounded text-xs font-semibold hover:bg-blue-600 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            onSelect(id || index);
          }}
        >
          Select
        </button>
      </div>
    </motion.div>
  );
};

export default FlightCard; 