import os
from dotenv import load_dotenv


def load_config() -> tuple[str, str]:
    """Load the Gemini API configuration from a local .env file."""
    # Force reload of .env to ignore stale environment variables
    load_dotenv(override=True)

    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key or api_key in ('your_api_key_here', 'Enter_api_key_here'):
        raise ValueError(
            'Missing GEMINI_API_KEY. Add your API key to .env'
        )

    model = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash').strip()
    return api_key, model