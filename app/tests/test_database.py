import os
import asyncio
from supabase.client import create_client, Client
from dotenv import load_dotenv
import uuid
from datetime import datetime, timedelta
import traceback

# Load environment variables
load_dotenv()

# Debug: Print environment variables (without sensitive data)
print("\nEnvironment Variables Check:")
print(f"SUPABASE_URL exists: {bool(os.getenv('SUPABASE_URL'))}")
print(f"SUPABASE_KEY exists: {bool(os.getenv('SUPABASE_KEY'))}")
print(f"SUPABASE_DB_PASSWORD exists: {bool(os.getenv('SUPABASE_DB_PASSWORD'))}")

def test_database_setup():
    """Test the database setup and basic operations."""
    try:
        # Initialize Supabase client
        print("\nInitializing Supabase client...")
        supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        print("✅ Supabase client initialized")
        
        # Test user creation
        print("\nTesting user creation...")
        test_user = {
            "email": f"test_{uuid.uuid4()}@example.com"
        }
        user_response = supabase.table("users").insert(test_user).execute()
        print("✅ Successfully created test user")
        
        # Test trip creation
        print("\nTesting trip creation...")
        start_date = datetime.now().date()
        end_date = (datetime.now() + timedelta(days=3)).date()
        test_trip = {
            "user_id": user_response.data[0]["id"],
            "destination": "Paris",
            "start_date": start_date.isoformat(),  # Convert to ISO format string
            "end_date": end_date.isoformat(),      # Convert to ISO format string
        }
        trip_response = supabase.table("trips").insert(test_trip).execute()
        print("✅ Successfully created test trip")
        
        # Test trip state creation
        print("\nTesting trip state creation...")
        test_state = {
            "trip_id": trip_response.data[0]["id"],
            "session_id": str(uuid.uuid4()),
            "state": {
                "current_step": "planning",
                "progress": 0.5
            }
        }
        state_response = supabase.table("trip_states").insert(test_state).execute()
        print("✅ Successfully created test trip state")
        
        # Test place creation
        print("\nTesting place creation...")
        test_place = {
            "name": "Eiffel Tower",
            "type": "attraction",
            "location": {
                "lat": 48.8584,
                "lng": 2.2945
            },
            "details": {
                "description": "Iconic iron lattice tower",
                "rating": 4.7
            }
        }
        place_response = supabase.table("places").insert(test_place).execute()
        print("✅ Successfully created test place")
        
        # Test full-text search
        print("\nTesting full-text search...")
        search_response = supabase.table("places")\
            .select("*")\
            .text_search("name", "Eiffel")\
            .execute()
        
        if search_response.data:
            print("✅ Successfully tested full-text search")
        
        # Clean up test data
        print("\nCleaning up test data...")
        supabase.table("trip_states").delete().eq("trip_id", trip_response.data[0]["id"]).execute()
        supabase.table("trips").delete().eq("id", trip_response.data[0]["id"]).execute()
        supabase.table("users").delete().eq("id", user_response.data[0]["id"]).execute()
        supabase.table("places").delete().eq("id", place_response.data[0]["id"]).execute()
        print("✅ Successfully cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing database setup:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_database_setup() 