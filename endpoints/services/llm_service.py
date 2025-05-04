import os
from anthropic import Anthropic

def parse_user_input(input_text):
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError('ANTHROPIC_API_KEY environment variable not set')
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3-haiku-20240307",  # or another Claude model you have access to
        max_tokens=512,
        messages=[{"role": "user", "content": input_text}]
    )
    return response.content[0].text if response.content else "No response from LLM." 