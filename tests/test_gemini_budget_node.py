import asyncio
from app.nodes.agents.budget_node import search_real_prices

async def test_search_real_prices():
    test_cases = [
        {"location": "Paris", "category": "hotel", "preferences": ["luxury"]},
        {"location": "Tokyo", "category": "food", "preferences": ["sushi", "fine dining"]},
        {"location": "London", "category": "activities", "preferences": ["museums", "theatre"]},
    ]
    for case in test_cases:
        print(f"\nTesting {case['category']} prices in {case['location']} with preferences {case['preferences']}")
        result = await search_real_prices(case["location"], case["category"], case["preferences"])
        print("Result:", result)
        assert all(key in result for key in ["min_price", "max_price", "average_price", "details"]), "Missing keys in result"
        assert isinstance(result["min_price"], (int, float)), "min_price should be a number"
        assert isinstance(result["max_price"], (int, float)), "max_price should be a number"
        assert isinstance(result["average_price"], (int, float)), "average_price should be a number"
        print("Test passed.")

if __name__ == "__main__":
    asyncio.run(test_search_real_prices()) 