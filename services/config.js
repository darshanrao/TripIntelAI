// TripIntelAI API Configuration
const USE_MOCK_API = true; // Set to false to use real API

// API URLs
const REAL_API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const MOCK_API_URL = 'http://localhost:8000'; // Mock backend URL

// Export the configuration
export const API_URL = USE_MOCK_API ? MOCK_API_URL : REAL_API_URL;
export const USE_MOCKS = USE_MOCK_API;

// Debugging information
if (typeof window !== 'undefined') {
  console.log(`TripIntelAI API Config:`);
  console.log(`- Using ${USE_MOCK_API ? 'MOCK' : 'REAL'} API`);
  console.log(`- API URL: ${API_URL}`);
} 