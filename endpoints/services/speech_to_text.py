import os
import requests
from dotenv import load_dotenv

load_dotenv()

def transcribe_audio(file_path):
    api_key = os.getenv('DEEPGRAM_API_KEY')
    print(f"[DEBUG] Using DEEPGRAM_API_KEY: {'SET' if api_key else 'NOT SET'}")
    if not api_key:
        raise ValueError('DEEPGRAM_API_KEY environment variable not set')

    url = 'https://api.deepgram.com/v1/listen'
    headers = {
        'Authorization': f'Token {api_key}',
    }
    file_size = os.path.getsize(file_path)
    file_ext = os.path.splitext(file_path)[1]
    print(f"[DEBUG] File to upload: {file_path}, Size: {file_size} bytes, Extension: {file_ext}")
    response = None
    try:
        with open(file_path, 'rb') as audio_file:
            response = requests.post(url, headers=headers, files={'file': audio_file})
        print(f"[DEBUG] Deepgram API response status: {response.status_code}")
        data = response.json()
        print(f"[DEBUG] Deepgram API response JSON: {data}")
        response.raise_for_status()
        # Return only the main transcript string
        transcript = data['results']['channels'][0]['alternatives'][0]['transcript']
        return transcript
    except Exception as e:
        if response is not None:
            print(f"[ERROR] Deepgram API error content: {response.content}")
        print(f"[ERROR] Exception during transcription: {e}")
        raise 