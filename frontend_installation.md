# Travel Itinerary AI - Frontend Installation

This document provides instructions for setting up and running the frontend of the Travel Itinerary AI application.

## Prerequisites

- Node.js (v14 or newer)
- npm or yarn
- Google Maps API key (for map functionality)

## Installation Steps

1. **Install dependencies**:
   ```bash
   npm install
   # or
   yarn install
   ```

2. **Configure environment variables**:

   Create a `.env.local` file in the root directory with the following content:
   ```
   NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

   Replace `your_google_maps_api_key_here` with your actual Google Maps API key.

3. **Start the development server**:
   ```bash
   npm run dev
   # or
   yarn dev
   ```

4. **Access the application**:
   Open [http://localhost:3000](http://localhost:3000) in your browser.

## Backend Integration

Make sure the FastAPI backend is running on http://localhost:8000 or update the `NEXT_PUBLIC_API_URL` in your `.env.local` file to point to the correct backend URL.

## Building for Production

To create a production build:

```bash
npm run build
# or
yarn build
```

To start the production server:

```bash
npm run start
# or
yarn start
```

## Troubleshooting

- **Map doesn't load**: Ensure your Google Maps API key is correct and has the necessary APIs enabled (Maps JavaScript API, Directions API, Places API).

- **Can't connect to backend**: Check that the backend server is running and the `NEXT_PUBLIC_API_URL` environment variable is set correctly.

- **Voice input not working**: Speech recognition is only available in supported browsers and requires HTTPS in production environments.

## Features and Layout

The application consists of a three-column layout:

1. **Left Column**: Chat interface with WhatsApp-style messaging and voice input
2. **Middle Column**: Itinerary view with day selector and activity timeline
3. **Right Column**: Google Maps with route visualization

On mobile devices, the layout switches to a tabbed interface for easy navigation between the three sections. 