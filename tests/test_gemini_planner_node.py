import asyncio
import pytest
from app.nodes.planner_node import agent_selector_node
from app.schemas.trip_schema import TripMetadata
from datetime import datetime

@pytest.mark.asyncio
async def test_agent_selector_node():
    # Sample user query and metadata
    user_query = "I want to go to Paris from New York for 5 days starting May 15th, 2024. I'm interested in museums and food."
    metadata = TripMetadata(
        source="New York",
        destination="Paris",
        start_date=datetime(2024, 5, 15),
        end_date=datetime(2024, 5, 20),
        num_people=2,
        preferences=["museums", "food"]
    )
    state = {
        "is_valid": True,
        "raw_query": user_query,
        "metadata": metadata,
        "error": None,
        "nodes_to_call": []
    }
    result = await agent_selector_node(state)
    print("Result:", result)
    assert "nodes_to_call" in result, "Missing nodes_to_call in result"
    assert isinstance(result["nodes_to_call"], list), "nodes_to_call should be a list"
    print("Test passed.")

if __name__ == "__main__":
    asyncio.run(test_agent_selector_node()) 