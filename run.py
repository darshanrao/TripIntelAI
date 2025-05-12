import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from app.main import main

if __name__ == "__main__":
    asyncio.run(main()) 