import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const ItineraryView = ({ days, selectedDay, onSelectDay }) => {
  const [activities, setActivities] = useState([]);
  const timelineRef = useRef(null);

  // Set activities whenever selectedDay changes
  useEffect(() => {
    // Handle case where days might be empty or undefined
    if (!days || days.length === 0) {
      setActivities([]);
      return;
    }

    const currentDayData = days.find(day => day.day === selectedDay);
    if (currentDayData) {
      setActivities(currentDayData.activities || []);
    } else {
      setActivities([]);
    }
  }, [days, selectedDay]);

  // Function to scroll to current time of day (if app is used during trip)
  const scrollToCurrentTime = () => {
    if (!timelineRef.current) return;
    
    const now = new Date();
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    
    // Find activity closest to current time
    const currentActivity = activities.find(activity => {
      const timeParts = activity.time.match(/(\d+):(\d+)\s*(AM|PM)/i);
      if (!timeParts) return false;
      
      let [_, hours, minutes, period] = timeParts;
      hours = parseInt(hours);
      minutes = parseInt(minutes);
      
      // Convert to 24-hour format
      if (period.toUpperCase() === 'PM' && hours < 12) hours += 12;
      if (period.toUpperCase() === 'AM' && hours === 12) hours = 0;
      
      // Activity is in the past or current
      return hours < currentHour || (hours === currentHour && minutes <= currentMinute);
    });
    
    if (currentActivity) {
      const index = activities.indexOf(currentActivity);
      const activityElements = timelineRef.current.querySelectorAll('.timeline-item');
      if (index >= 0 && activityElements[index]) {
        activityElements[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Days selector */}
      <div className="bg-gray-100 p-4">
        <div className="day-tabs flex space-x-2 overflow-x-auto pb-2">
          {days.map((day) => (
            <button
              key={day.day}
              onClick={() => onSelectDay(day.day)}
              className={`
                px-4 py-2 rounded-full text-sm font-medium transition-all
                ${selectedDay === day.day 
                  ? 'bg-secondary text-white shadow-md active' 
                  : 'bg-white text-gray-700 border'}
              `}
            >
              Day {day.day}
            </button>
          ))}
        </div>
      </div>
      
      {/* Itinerary timeline */}
      <div className="flex-1 overflow-y-auto p-4 timeline-container" ref={timelineRef}>
        <AnimatePresence mode="wait">
          <motion.div
            key={selectedDay}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
            className="space-y-6"
          >
            {activities.map((activity, index) => (
              <motion.div
                key={`${selectedDay}-${index}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className="flex timeline-item"
              >
                {/* Time column */}
                <div className="w-20 text-right pr-4">
                  <div className="text-sm font-semibold text-gray-600">{activity.time}</div>
                </div>
                
                {/* Timeline line and dot */}
                <div className="relative flex flex-col items-center">
                  <div className="h-full w-0.5 bg-gray-200 absolute top-0 bottom-0"></div>
                  <div className={`
                    z-10 rounded-full w-4 h-4 flex items-center justify-center
                    ${index === 0 ? 'bg-primary' : 'bg-secondary'}
                  `}>
                    <span className="text-white text-xs">{activity.icon}</span>
                  </div>
                </div>
                
                {/* Activity details */}
                <div className="ml-4 bg-white rounded-lg border border-gray-200 shadow-sm p-4 flex-1 mb-6">
                  <div className="flex items-center mb-2">
                    <span className="text-2xl mr-3">{activity.icon}</span>
                    <h3 className="font-semibold">{activity.title}</h3>
                  </div>
                  <p className="text-sm text-gray-600">{activity.description}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default ItineraryView; 