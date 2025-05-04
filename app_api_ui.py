import streamlit as st
import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="TripIntelAI - API Testing",
    page_icon="🌍",
    layout="wide",
)

# App title
st.title("🌍 TripIntelAI - API Testing Tool")
st.write("Use this tool to test the TripIntelAI API endpoint. Enter your travel query below.")

# Sidebar configuration
st.sidebar.header("API Configuration")
api_mode = st.sidebar.radio("API Mode", ["Normal API (port 8000)", "Mock API (port 8001)"])
api_port = 8001 if "Mock" in api_mode else 8000
api_url = st.sidebar.text_input("API URL", f"http://localhost:{api_port}/chat")

# Example queries
st.sidebar.header("Example Queries")
example_queries = [
    "I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people with focus on museums and good restaurants",
    "Plan a family vacation to Paris in June 2025 for 4 people with kids aged 5 and 8",
    "Weekend getaway to San Francisco in August 2025 for a couple interested in wineries and hiking",
    "Business trip to London for 3 days in December 2025 with some free time for sightseeing",
    "Beach vacation to Hawaii for 10 days in July 2025 for a family of 5"
]

# Display example queries
if st.sidebar.button("Load Example Query"):
    import random
    st.session_state.query = random.choice(example_queries)

# Help section
with st.sidebar.expander("Help & Information"):
    st.write("""
    ## How to Use
    1. Select the API mode (Normal or Mock)
    2. Enter your travel query in the text area
    3. Click "Generate Itinerary" to send the request
    4. View the results below
    
    ## Notes
    - The Normal API requires all services to be running
    - The Mock API is faster but uses simulated data
    - Processing can take 20-60 seconds depending on the query complexity
    """)

# Main query input
query = st.text_area(
    "Enter your travel query",
    height=100,
    key="query",
    help="Specify your travel details: destination, dates, number of people, preferences, etc.",
    placeholder="Example: I want to plan a trip from Boston to NYC from May 15 to May 18, 2025 for 2 people with focus on museums and good restaurants"
)

# Process button
process_button = st.button("Generate Itinerary", type="primary")

# Function to call API and display results
def call_api_and_display(query, api_url):
    start_time = time.time()
    
    # Create a placeholder for the progress
    progress_placeholder = st.empty()
    progress_bar = progress_placeholder.progress(0)
    status_text = st.empty()
    
    # Animation for processing stages
    processing_stages = [
        "Initializing travel planner...",
        "Analyzing your travel query...",
        "Extracting travel details...",
        "Validating trip parameters...",
        "Planning trip components...",
        "Searching for flights...",
        "Finding places to visit...",
        "Discovering local restaurants...",
        "Locating suitable accommodations...",
        "Calculating your trip budget...",
        "Analyzing reviews for better recommendations...",
        "Generating your personalized itinerary..."
    ]
    
    # Prepare the request payload
    payload = {
        "query": query
    }
    
    try:
        # Start animation
        for i, stage in enumerate(processing_stages):
            progress = min(0.95, (i+1) / len(processing_stages))
            progress_bar.progress(progress)
            status_text.write(f"🔄 {stage}")
            # Pause slightly longer at the beginning, shorter at the end for a more realistic feel
            time.sleep(max(0.5, 2 - (i/len(processing_stages)*1.5)))
        
        # Make the API request
        progress_bar.progress(0.97)
        status_text.write("🔄 Finalizing and receiving response...")
        
        response = requests.post(api_url, json=payload, timeout=60)
        
        # Calculate elapsed time
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Clear the progress indicators
        progress_placeholder.empty()
        status_text.empty()
        
        # Process the response
        if response.status_code == 200:
            result = response.json()
            
            # Check if we have an itinerary
            if result.get("itinerary"):
                st.success(f"✅ Itinerary generated successfully in {elapsed_time:.2f} seconds")
                
                # Display the itinerary in a nice box
                with st.container():
                    st.subheader("📝 Your Personalized Travel Itinerary")
                    st.markdown(f"""
                    <div style="background-color:#f0f2f6;padding:20px;border-radius:10px;">
                    {result["itinerary"].replace('\n', '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Display any suggestions
                if result.get("suggestions"):
                    with st.expander("Trip Suggestions"):
                        for suggestion in result["suggestions"]:
                            st.write(f"• {suggestion}")
            
            # Display validation errors
            elif not result.get("is_valid", True):
                st.error("❌ Your travel query couldn't be processed")
                with st.expander("Validation Errors"):
                    for error in result.get("validation_errors", []):
                        st.write(f"• {error}")
            
            # Other errors
            else:
                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
        
        else:
            st.error(f"❌ Request failed with status code {response.status_code}")
            st.code(response.text)
        
        # Display raw response for debugging
        with st.expander("Raw API Response"):
            st.json(response.json() if response.status_code == 200 else {"error": response.text})
        
    except Exception as e:
        # Clear the progress indicators
        progress_placeholder.empty()
        status_text.empty()
        
        st.error(f"❌ Exception: {str(e)}")
        st.info("Make sure the API server is running and accessible.")

# When process button is clicked
if process_button and query:
    call_api_and_display(query, api_url)
elif process_button and not query:
    st.warning("Please enter a travel query first.")

# Footer
st.markdown("---")
st.markdown("*TripIntelAI API Testing Tool - Made with Streamlit*") 