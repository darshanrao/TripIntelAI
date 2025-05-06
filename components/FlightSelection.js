import React from 'react';
import FlightCard from './FlightCard';
import { motion } from 'framer-motion';

const FlightSelection = ({ flights, onSelectFlight }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="w-full bg-gray-50 rounded-lg p-3 my-2"
    >
      <div className="text-center mb-2">
        <h3 className="text-base font-semibold text-gray-800">Select a flight</h3>
        <p className="text-xs text-gray-600">
          Choose the flight that best meets your needs
        </p>
      </div>
      
      <div className="grid grid-cols-2 gap-2">
        {flights.map((flight, index) => (
          <FlightCard 
            key={flight.id || index}
            flight={flight}
            index={index}
            onSelect={onSelectFlight}
          />
        ))}
      </div>
      
      <div className="text-center mt-2">
        <p className="text-xs text-gray-500">
          Showing {flights.length} flights • Prices include taxes and fees
        </p>
      </div>
    </motion.div>
  );
};

export default FlightSelection; 