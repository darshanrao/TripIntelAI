# Travel Itinerary AI Frontend

This is the frontend for the Travel Itinerary AI Assistant web application. It provides a user-friendly interface for interacting with the AI travel planner.

## Features

- **Three-Column Layout**:
  - WhatsApp-style chat interface for communicating with the AI
  - Interactive itinerary view with daily activities
  - Google Maps integration showing routes between locations

- **Responsive Design**:
  - Works on mobile and desktop devices
  - Tabs navigation on mobile for easy access to different sections

- **Interactive Elements**:
  - Speech-to-text for voice input
  - Day selector for navigating multi-day itineraries
  - Animated timeline view for activities
  - Route visualization on the map

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Set up Environment Variables**:
   Create a `.env.local` file in the root directory with the following content:
   ```
   NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_MAPS_API_KEY_HERE
   ```
   Replace `YOUR_GOOGLE_MAPS_API_KEY_HERE` with your actual Google Maps API key.

3. **Run the Development Server**:
   ```bash
   npm run dev
   ```

4. **Access the Application**:
   Open [http://localhost:3000](http://localhost:3000) in your browser.

## Integration with Backend

The frontend is designed to work with the FastAPI backend. The chat interface sends user messages to the backend API and displays the responses. The itinerary view and map are updated based on the data received from the backend.

## Folder Structure

- `components/` - React components
  - `ChatInterface.js` - WhatsApp-style chat with voice input
  - `ItineraryView.js` - Calendar-style itinerary with timeline
  - `MapView.js` - Google Maps integration with route display
- `pages/` - Next.js pages
  - `index.js` - Main page with three-column layout
  - `_app.js` - Next.js app configuration
- `styles/` - CSS styles
  - `globals.css` - Global styles and animations

## Technologies Used

- React and Next.js
- Tailwind CSS for styling
- Framer Motion for animations
- Google Maps JavaScript API
- Web Speech API for voice input

## Customization

- Colors and styles can be customized in `tailwind.config.js`
- Animations can be adjusted in `styles/globals.css`
- Sample itinerary data is in `pages/index.js` - replace with API data in production 