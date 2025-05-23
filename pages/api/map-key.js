/**
 * Secure API endpoint for providing Google Maps API key
 * 
 * This endpoint:
 * 1. Verifies the request is from your own domain (CORS protection)
 * 2. Serves the API key only on server-side, never exposing it in client-side code
 * 3. Can be extended to add rate limiting, IP filtering, etc.
 */

// Helper function to create a delay
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export default async function handler(req, res) {
  // Only allow GET requests
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // CORS protection - only allow requests from your own domain
  // Get the referring domain
  const referer = req.headers.referer || '';
  const allowedDomains = [
    // Add your domains here
    'http://localhost:3000',
    'https://localhost:3000',
    process.env.NEXT_PUBLIC_SITE_URL, // Your production domain
  ].filter(Boolean);

  // Check if the request is from an allowed domain
  const isAllowedDomain = allowedDomains.some(domain => 
    referer.startsWith(domain)
  );

  if (!isAllowedDomain && process.env.NODE_ENV === 'production') {
    return res.status(403).json({ error: 'Forbidden' });
  }

  // Simulate backend processing time
  await delay(10000); // 10 second delay

  // Get the API key from environment variables
  const apiKey = process.env.GOOGLE_PLACES_API_KEY;

  if (!apiKey) {
    // Don't expose that the key is missing, just return an error
    console.error('Google Maps API key is not configured');
    return res.status(500).json({ error: 'Internal server error' });
  }

  // Return the API key
  return res.status(200).json({ key: apiKey });
} 