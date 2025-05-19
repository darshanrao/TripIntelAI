import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

async def test_supabase_connection():
    """Test the Supabase connection and basic operations."""
    try:
        # Initialize Supabase client
        supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
        
        # Test connection by inserting a test record
        test_session_id = str(uuid.uuid4())  # Generate a proper UUID
        test_data = {
            "session_id": test_session_id,
            "state": {"test": "data"}
        }
        
        # Insert test data
        response = await supabase.table("trip_states").insert(test_data).execute()
        print("✅ Successfully inserted test data")
        
        # Retrieve test data
        response = await supabase.table("trip_states")\
            .select("*")\
            .eq("session_id", test_session_id)\
            .execute()
        
        if response.data:
            print("✅ Successfully retrieved test data")
            print(f"Retrieved data: {response.data}")
        
        # Clean up test data
        await supabase.table("trip_states")\
            .delete()\
            .eq("session_id", test_session_id)\
            .execute()
        print("✅ Successfully cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Supabase connection: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_supabase_connection()) 