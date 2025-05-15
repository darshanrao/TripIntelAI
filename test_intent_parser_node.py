import asyncio
from app.nodes.intent_parser_node import intent_parser_node

async def test():
    result = await intent_parser_node({'query': 'I want to go to New York City from Boston next month for 3 days'})
    print('Result:', result)

if __name__ == "__main__":
    asyncio.run(test()) 