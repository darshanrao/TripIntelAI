import React from 'react';
import TravelPlanner from '../components/TravelPlanner';

const TravelPlannerPage = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold text-gray-900">TripIntelAI</h1>
        </div>
      </header>
      <main>
        <TravelPlanner />
      </main>
    </div>
  );
};

export default TravelPlannerPage; 