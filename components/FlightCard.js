import React from 'react';
import { FaPlaneDeparture, FaPlaneArrival, FaClock, FaMoneyBillWave } from 'react-icons/fa';
import { motion } from 'framer-motion';

const FlightCard = ({ flight, index, onSelect }) => {
  // Extract flight data
  const { 
    airline, 
    flight_number: flightNumber, 
    departure_time: departureTime, 
    arrival_time: arrivalTime, 
    price, 
    currency = 'USD' 
  } = flight;

  // Format date and time
  const formatDateTime = (dateTimeStr) => {
    try {
      const date = new Date(dateTimeStr);
      return {
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
        time: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
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

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
      onClick={() => onSelect(index)}
    >
      <div className="p-4">
        <div className="flex justify-between items-center mb-3">
          <div className="text-lg font-semibold text-primary">
            {airline} {flightNumber}
          </div>
          <div className="text-lg font-bold text-green-600">
            <div className="flex items-center">
              <FaMoneyBillWave className="mr-1" />
              <span>${typeof price === 'number' ? price.toFixed(2) : price} {currency}</span>
            </div>
          </div>
        </div>
        
        <div className="flex justify-between mb-4">
          {/* Departure */}
          <div className="flex-1">
            <div className="flex items-center text-gray-600 mb-1">
              <FaPlaneDeparture className="mr-2" />
              <span className="font-semibold">Departure</span>
            </div>
            <div className="text-lg font-bold">{departure.time}</div>
            <div className="text-sm text-gray-600">{departure.date}</div>
          </div>
          
          {/* Duration */}
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="text-sm text-gray-500 mb-1">
              <FaClock className="inline mr-1" />
              <span>{duration}</span>
            </div>
            <div className="w-full flex items-center">
              <div className="h-[2px] flex-grow bg-gray-300"></div>
              <div className="px-2">✈️</div>
              <div className="h-[2px] flex-grow bg-gray-300"></div>
            </div>
          </div>
          
          {/* Arrival */}
          <div className="flex-1 text-right">
            <div className="flex items-center justify-end text-gray-600 mb-1">
              <span className="font-semibold">Arrival</span>
              <FaPlaneArrival className="ml-2" />
            </div>
            <div className="text-lg font-bold">{arrival.time}</div>
            <div className="text-sm text-gray-600">{arrival.date}</div>
          </div>
        </div>
        
        <button 
          className="w-full py-2 bg-primary text-white rounded-md hover:bg-blue-600 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            onSelect(index);
          }}
        >
          Select This Flight
        </button>
      </div>
    </motion.div>
  );
};

export default FlightCard; 