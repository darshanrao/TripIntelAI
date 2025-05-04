import React from 'react';
import FlightCard from './FlightCard';
import { motion } from 'framer-motion';

const FlightSelection = ({ flights, onSelectFlight }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="w-full bg-gray-50 rounded-lg p-5 my-4"
    >
      <div className="text-center mb-4">
        <h3 className="text-lg font-semibold text-gray-800">Please select a flight</h3>
        <p className="text-sm text-gray-600">
          Choose the flight that best meets your needs for this trip
        </p>
      </div>
      
      <div className="grid grid-cols-1 gap-4">
        {flights.map((flight, index) => (
          <FlightCard 
            key={index}
            flight={flight}
            index={index}
            onSelect={onSelectFlight}
          />
        ))}
      </div>
    </motion.div>
  );
};

export default FlightSelection; 