// Mock data for TripIntel frontend
// This is a copy of the data from mock-backend/mockData.js formatted for ES modules

// Mock itinerary data
export const mockItineraryData = {
   "trip_summary":{
      "destination":"Los Angeles",
      "start_date":"2025-06-10",
      "end_date":"2025-06-13",
      "duration_days":4,
      "total_budget":4729.13
   },
   "daily_itinerary":{
      "day_1":{
         "date":"2025-06-10",
         "activities":[
            {
               "type":"accommodation",
               "category":"hotel",
               "title":"Check-in at The Ritz-Carlton, Los Angeles",
               "time":"15:00",
               "duration_minutes":60,
               "details":{
                  "location":"900 West Olympic Boulevard, Los Angeles",
                  "latitude":34.0452145,
                  "longitude":-118.2666588
               },
               "review_insights":{
                  "sentiment":"positive",
                  "strengths":[
                     "Luxurious and elegant accommodations",
                     "Exceptional service and attentive staff"
                  ],
                  "weaknesses":[
                     "Expensive room rates and additional fees"
                  ],
                  "summary":"The Ritz-Carlton, Los Angeles offers a luxurious five-star experience with exceptional service, though guests should be prepared for premium pricing."
               }
            },
            {
               "type":"dining",
               "category":"dinner",
               "title":"Dinner at Eastside Italian Deli",
               "time":"19:00",
               "duration_minutes":90,
               "details":{
                  "location":"1013 Alpine Street, Los Angeles",
                  "latitude":34.0651255,
                  "longitude":-118.2466235
               },
               "review_insights":{
                  "sentiment":"positive",
                  "strengths":[
                     "Authentic Italian sandwiches and food",
                     "High-quality ingredients and meats"
                  ],
                  "weaknesses":[
                     "Long lines, especially during lunch hours"
                  ],
                  "summary":"Eastside Italian Deli is a beloved, family-owned Italian deli known for authentic, high-quality sandwiches and imported Italian goods, despite long lines."
               }
            }
         ]
      },
      "day_2":{
         "date":"2025-06-11",
         "activities":[
            {
               "type":"attraction",
               "category":"theme park",
               "title":"Visit Universal Studios Hollywood",
               "time":"09:00",
               "duration_minutes":480,
               "details":{
                  "location":"100 Universal City Plaza, Universal City",
                  "latitude":34.1419225,
                  "longitude":-118.358411
               },
               "review_insights":{
                  "sentiment":"positive",
                  "strengths":[
                     "Harry Potter Wizarding World attracts many visitors",
                     "Super Nintendo World is highly praised for its immersive experience"
                  ],
                  "weaknesses":[
                     "High ticket prices and expensive food/merchandise",
                     "Crowds and long wait times, especially on weekends and holidays"
                  ],
                  "summary":"Universal Studios Hollywood offers immersive themed areas like Wizarding World of Harry Potter and Super Nintendo World, alongside high prices and crowds during peak periods."
               }
            },
            {
               "type":"dining",
               "category":"dinner",
               "title":"Dinner at Sushi Gen",
               "time":"19:00",
               "duration_minutes":90,
               "details":{
                  "location":"422 East 2nd Street, Los Angeles",
                  "latitude":34.0467296,
                  "longitude":-118.2387113
               },
               "review_insights":{
                  "sentiment":"positive",
                  "strengths":[
                     "Fresh, high-quality fish",
                     "Excellent sashimi deluxe lunch special"
                  ],
                  "weaknesses":[
                     "Long wait times, especially during peak hours",
                     "Limited seating and crowded dining area"
                  ],
                  "summary":"Sushi Gen is renowned for its exceptionally fresh fish and famous sashimi deluxe lunch special at reasonable prices, despite consistently long wait times."
               }
            }
         ]
      },
      "day_3":{
         "date":"2025-06-12",
         "activities":[
            {
               "type":"attraction",
               "category":"park",
               "title":"Visit Griffith Park",
               "time":"09:00",
               "duration_minutes":240,
               "details":{
                  "location":"Los Angeles",
                  "latitude":34.0536909,
                  "longitude":-118.242766
               },
               "review_insights":{
                  "sentiment":"positive",
                  "strengths":[
                     "Breathtaking views of Los Angeles and the Hollywood Sign",
                     "Extensive hiking trails for all skill levels"
                  ],
                  "weaknesses":[
                     "Limited parking, especially on weekends and holidays",
                     "Heavy crowds during peak times"
                  ],
                  "summary":"Griffith Park offers stunning city views, extensive hiking trails, and attractions like the Griffith Observatory, though visitors should arrive early to avoid parking challenges and crowds."
               }
            },
            {
               "type":"dining",
               "category":"lunch",
               "title":"Lunch at Philippe The Original",
               "time":"12:30",
               "duration_minutes":90,
               "details":{
                  "location":"1001 North Alameda Street, Los Angeles",
                  "latitude":34.0596738,
                  "longitude":-118.236941
               },
               "review_insights":{
                  "sentiment":"positive",
                  "strengths":[
                     "Famous French dip sandwiches",
                     "Historic establishment (opened in 1908)"
                  ],
                  "weaknesses":[
                     "Long lines during peak hours",
                     "Limited seating during busy times"
                  ],
                  "summary":"Philippe The Original is a historic Los Angeles landmark famous for inventing the French dip sandwich in 1908, despite occasional long lines."
               }
            },
            {
               "type":"attraction",
               "category":"stadium",
               "title":"Visit Dodger Stadium",
               "time":"18:00",
               "duration_minutes":240,
               "details":{
                  "location":"1000 Vin Scully Ave, Los Angeles",
                  "latitude":34.0736255,
                  "longitude":-118.2398452
               },
               "review_insights":{
                  "sentiment":"positive",
                  "strengths":[
                     "Historic ballpark with iconic views of Los Angeles",
                     "Great baseball atmosphere and experience"
                  ],
                  "weaknesses":[
                     "Expensive parking ($30-35)",
                     "Traffic congestion before and after games"
                  ],
                  "summary":"Dodger Stadium offers an iconic baseball experience with beautiful views, though visitors should plan for expensive parking and traffic congestion."
               }
            }
         ]
      },
      "day_4":{
         "date":"2025-06-13",
         "activities":[
            {
               "type":"attraction",
               "category":"museum",
               "title":"Visit The Getty",
               "time":"09:00",
               "duration_minutes":240,
               "details":{
                  "location":"1200 Getty Center Drive, Los Angeles",
                  "latitude":34.0769513,
                  "longitude":-118.475712
               },
               "review_insights":{
                  "sentiment":"positive",
                  "strengths":[
                     "Stunning architecture and views",
                     "Impressive art collection"
                  ],
                  "weaknesses":[
                     "Expensive parking ($20-25)",
                     "Crowded during peak times and weekends"
                  ],
                  "summary":"The Getty offers a world-class cultural experience with stunning architecture and art, though visitors should plan for parking costs and potential crowds."
               }
            },
            {
               "type":"dining",
               "category":"lunch",
               "title":"Lunch at Bottega Louie",
               "time":"13:00",
               "duration_minutes":90,
               "details":{
                  "location":"700 South Grand Avenue, Los Angeles",
                  "latitude":34.047143,
                  "longitude":-118.256605
               },
               "review_insights":{
                  "sentiment":"positive",
                  "strengths":[
                     "High-quality pastries and macarons",
                     "Beautiful interior and ambiance"
                  ],
                  "weaknesses":[
                     "Long wait times, especially on weekends",
                     "Expensive prices"
                  ],
                  "summary":"Bottega Louie is known for its beautiful interior, photogenic desserts, and European-inspired menu, though it can be crowded with long waits and high prices."
               }
            },
            {
               "type":"transportation",
               "category":"flight",
               "title":"Depart Los Angeles on UA505",
               "time":"18:00",
               "duration_minutes":101,
               "details":{
                  "airline":"UA",
                  "flight_number":"UA505",
                  "departure_time":"2025-06-13T06:00:00",
                  "arrival_time":"2025-06-13T07:41:00"
               }
            },
            {
               "type":"accommodation",
               "category":"hotel",
               "title":"Check-out from The Ritz-Carlton, Los Angeles",
               "time":"12:00",
               "duration_minutes":30,
               "details":{
                  "location":"900 West Olympic Boulevard, Los Angeles",
                  "latitude":34.0452145,
                  "longitude":-118.2666588
               }
            }
         ]
      }
   },
   "review_highlights":{
      "top_rated_places":[],
      "top_rated_restaurants":[],
      "hotel_review_summary":{
         "name":"The Ritz-Carlton, Los Angeles",
         "rating":4.6,
         "strengths":[
            "Luxurious and elegant accommodations",
            "Exceptional service and attentive staff",
            "Prime downtown LA location",
            "High-quality dining options",
            "Impressive city views",
            "Rooftop pool",
            "Well-appointed rooms with modern amenities",
            "Spa facilities"
         ],
         "weaknesses":[
            "Expensive room rates and additional fees",
            "Some rooms considered small for the price",
            "Parking is costly",
            "Occasional service inconsistencies",
            "Dated decor in some areas",
            "Crowded pool area during peak times"
         ],
         "summary":"The Ritz-Carlton, Los Angeles offers a luxurious five-star experience in downtown LA with exceptional service, elegant accommodations, and convenient access to LA Live entertainment complex. While consistently praised for its attentive staff and upscale amenities, guests should be prepared for premium pricing and occasional crowding in common areas."
      },
      "overall": ["Great weather", "Diverse attractions", "Celebrity spotting"],
      "accommodations": ["Luxury hotels", "Beachfront properties", "Celebrity hotspots"],
      "dining": ["Diverse cuisine", "Celebrity restaurants", "Food trucks"],
      "attractions": ["Hollywood", "Universal Studios", "Beaches", "Getty Museum"]
   }
};

// Mock flight data
export const mockFlights = [
  {
    id: "UA505",
    airline: "United Airlines",
    flight_number: "UA505",
    departure_airport: "LAX",
    arrival_airport: "SFO",
    departure_time: "2025-06-13T06:00:00",
    arrival_time: "2025-06-13T07:41:00",
    price: 249,
    duration_minutes: 101,
    stops: 0,
    aircraft: "Boeing 737-900"
  },
  {
    id: "AA1525",
    airline: "American Airlines",
    flight_number: "AA1525",
    departure_airport: "LAX",
    arrival_airport: "SFO",
    departure_time: "2025-06-13T08:30:00",
    arrival_time: "2025-06-13T10:05:00",
    price: 189,
    duration_minutes: 95,
    stops: 0,
    aircraft: "Airbus A321"
  },
  {
    id: "DL675",
    airline: "Delta Air Lines",
    flight_number: "DL675",
    departure_airport: "LAX",
    arrival_airport: "SFO",
    departure_time: "2025-06-13T10:15:00",
    arrival_time: "2025-06-13T11:52:00",
    price: 219,
    duration_minutes: 97,
    stops: 0,
    aircraft: "Boeing 737-800"
  },
  {
    id: "AS1296",
    airline: "Alaska Airlines",
    flight_number: "AS1296",
    departure_airport: "LAX",
    arrival_airport: "SFO",
    departure_time: "2025-06-13T13:45:00",
    arrival_time: "2025-06-13T15:20:00",
    price: 179,
    duration_minutes: 95,
    stops: 0,
    aircraft: "Boeing 737-900"
  },
  {
    id: "WN1422",
    airline: "Southwest Airlines",
    flight_number: "WN1422",
    departure_airport: "LAX",
    arrival_airport: "SFO",
    departure_time: "2025-06-13T16:30:00",
    arrival_time: "2025-06-13T18:05:00",
    price: 159,
    duration_minutes: 95,
    stops: 0,
    aircraft: "Boeing 737-700"
  }
];

// Sample chat responses based on keywords
export const chatResponses = {
  default: "I understand you're interested in traveling. Can you tell me where you'd like to go and when?",
  hello: "Hi there! I'm your AI travel assistant. Where would you like to go?",
  los_angeles: "Los Angeles is a fantastic destination! Known for its sunny weather, iconic beaches, Hollywood glamour, and diverse dining scene. When are you planning to visit?",
  la: "Los Angeles is a fantastic destination! Known for its sunny weather, iconic beaches, Hollywood glamour, and diverse dining scene. When are you planning to visit?",
  hollywood: "Hollywood is an iconic part of Los Angeles known for the film industry, Walk of Fame, and landmarks like the Hollywood sign. Would you like to include it in your itinerary?",
  budget: "Your total budget of $4729.13 should be sufficient for a luxury experience in Los Angeles, including accommodations at The Ritz-Carlton, dining, and attractions.",
  flight: "I've found several flight options for your departure from Los Angeles. The United Airlines flight UA505 appears to be a good option with a morning departure time.",
  itinerary: "I've prepared a detailed 4-day itinerary for your Los Angeles trip. It includes luxury accommodations at The Ritz-Carlton, visits to Universal Studios, Griffith Park, and the Getty Museum, as well as excellent dining options.",
  hotel: "For your stay in Los Angeles, I've selected The Ritz-Carlton, a luxurious five-star hotel with exceptional service, elegant accommodations, and convenient access to downtown LA attractions.",
  food: "Los Angeles has an incredible dining scene! I've included a variety of options in your itinerary, from the beloved Eastside Italian Deli to the popular Sushi Gen and the historic Philippe The Original.",
  activity: "Los Angeles offers countless activities! Your itinerary includes Universal Studios Hollywood with its immersive Harry Potter and Nintendo areas, Griffith Park with stunning city views, Dodger Stadium for baseball fans, and the Getty Museum for art lovers."
};

// Helper function for simulating network delay
export const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Mock chat history
export const mockChatHistory = [
  {
    id: 1,
    text: "Hello, I'm planning a trip to Los Angeles. Can you help me?",
    sender: "user",
    timestamp: new Date(Date.now() - 86400000)
  },
  {
    id: 2,
    text: "Hi there! I'd be happy to help you plan your trip to Los Angeles. Could you tell me when you're planning to visit and how long you'll be staying?",
    sender: "ai",
    timestamp: new Date(Date.now() - 86390000)
  }
]; 