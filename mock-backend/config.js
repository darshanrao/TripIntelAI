// Configuration for the mock backend
module.exports = {
  // Server configuration
  port: process.env.PORT || 8000,
  host: process.env.HOST || 'localhost',
  
  // API configuration
  apiPrefix: '/api/v1',
  
  // Delay settings (in milliseconds)
  delays: {
    min: 300,  // Minimum delay for API responses
    max: 2000, // Maximum delay for API responses
  },
  
  // CORS settings
  cors: {
    origin: '*', // Allow all origins
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  },
  
  // WebSocket configuration
  websocket: {
    enabled: false, // WebSocket is mocked, not fully implemented
    path: '/ws',
  },
}; 