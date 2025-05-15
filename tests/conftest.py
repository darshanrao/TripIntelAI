import os
import sys
import pytest
from dotenv import load_dotenv

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    # Set test-specific environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['FLASK_APP'] = 'app.py'
    os.environ['FLASK_DEBUG'] = '1'
    os.environ['GOOGLE_PLACES_API_KEY'] = 'test_api_key'
    os.environ['PERPLEXITY_API_KEY'] = 'test_perplexity_key'
    os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
    
    yield
    
    # Cleanup after tests
    env_vars = [
        'FLASK_ENV',
        'FLASK_APP',
        'FLASK_DEBUG',
        'GOOGLE_PLACES_API_KEY',
        'PERPLEXITY_API_KEY',
        'GEMINI_API_KEY'
    ]
    for var in env_vars:
        if var in os.environ:
            del os.environ[var] 